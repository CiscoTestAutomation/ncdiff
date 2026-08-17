import pyang
import logging


logger = logging.getLogger(__name__)


def set_ordering_match(ctx, xpath_stmt, initial, node1, node2, operator):
    if not hasattr(xpath_stmt, 'raw_ordering_match'):
        xpath_stmt.raw_ordering_match = []
    match_item = (node1, operator, node2)
    if match_item not in xpath_stmt.raw_ordering_match:
        xpath_stmt.raw_ordering_match.append(match_item)

    n2 = get_function(node2, xpath_stmt)
    if n2 is not None:
        if not hasattr(xpath_stmt, 'ordering_match'):
            xpath_stmt.ordering_match = []
        if isinstance(n2, tuple):
            match_item = (node1, operator) + n2
        else:
            match_item = (node1, operator, n2, None)
        if match_item not in xpath_stmt.ordering_match:
            xpath_stmt.ordering_match.append(match_item)


def get_context_node(stmt):
    if stmt.parent.keyword == 'augment':
        node = stmt.parent.i_target_node
    elif stmt.parent.keyword == 'deviate':
        node = stmt.parent.parent.i_target_node
    elif (
        getattr(stmt, 'i_origin', None) == 'uses' and
        stmt.parent.keyword != 'choice'
    ):
        node = pyang.util.data_node_up(stmt.parent)
    else:
        node = stmt.parent
    if node is not None:
        node = pyang.util.closest_ancestor_data_node(node)
    return node


def get_function(tuple_info, xpath_stmt):
    """tuple_info is a tuple of the form (type, inputs). For example,
    ('number', [('object', ('substring-before', [('string', <pyang.LeafLeaflistStatement 'leaf name' at 0x7fe47ff10b80>), ('string', '.')]))])"""
    if not isinstance(tuple_info, tuple):
        return tuple_info
    func, args = tuple_info
    if func in ['substring-before', 'substring-after']:
        if len(args) != 2:
            logger.error(f"{func}() should have 2 arguments but actually has "
                         f"{len(args)}:\n{xpath_stmt.pos}")
            return None
        if args[1] != ('string', '.'):
            logger.error(f"{func}() should have the 2nd argument as '.' but "
                         f"actually '{args[1]}'. This requires an enhancement "
                         f"of ncdiff:\n{xpath_stmt.pos}")
            return None
        return (args[0][1], func)
    elif func == 'string':
        if len(args) != 1:
            logger.error(f"string() should have 1 argument but actually has "
                         f"{len(args)}:\n{xpath_stmt.pos}")
            return None
        return args[0][1]
    elif func == 'number':
        if len(args) != 1:
            logger.error(f"number() should have 1 argument but actually has "
                         f"{len(args)}:\n{xpath_stmt.pos}")
            return None
        return get_function(args[0][1], xpath_stmt)
    else:
        logger.warning(f"{func}() is not supported by the value matching "
                       f"feature\n{xpath_stmt.pos}")
        return None


def chk_xpath_expr(ctx, xpath_stmt, initial, node, q, t):
    mod = xpath_stmt.i_orig_module
    pos = xpath_stmt.pos

    if isinstance(q, list):
        return chk_xpath_path(ctx, xpath_stmt, initial, node, q)
    elif isinstance(q, tuple):
        if q[0] == 'absolute':
            return chk_xpath_path(ctx, xpath_stmt, initial, 'root', q[1])
        elif q[0] == 'relative':
            return chk_xpath_path(ctx, xpath_stmt, initial, node, q[1])
        elif q[0] == 'union':
            return [
                chk_xpath_path(ctx, xpath_stmt, initial, node, qa)
                for qa in q[1]
            ]
        elif q[0] == 'comp':
            node1 = chk_xpath_expr(ctx, xpath_stmt, initial, node, q[2], None)
            node2 = chk_xpath_expr(ctx, xpath_stmt, initial, node, q[3], None)
            set_ordering_match(ctx, xpath_stmt, initial, node1, node2, q[1])
        elif q[0] == 'arith':
            chk_xpath_expr(ctx, xpath_stmt, initial, node, q[2], None)
            chk_xpath_expr(ctx, xpath_stmt, initial, node, q[3], None)
        elif q[0] == 'bool':
            chk_xpath_expr(ctx, xpath_stmt, initial, node, q[2], None)
            chk_xpath_expr(ctx, xpath_stmt, initial, node, q[3], None)
        elif q[0] == 'negative':
            chk_xpath_expr(ctx, xpath_stmt, initial, node, q[1], None)
        elif q[0] == 'function_call':
            rettype, ret, inputs = chk_xpath_function(ctx, xpath_stmt, initial, node, q[1], q[2])
            if ret is None:
                return q[1], inputs
            else:
                return ret
        elif q[0] == 'path_expr':
            return chk_xpath_expr(ctx, xpath_stmt, initial, node, q[1], t)
            # return sth
        elif q[0] == 'path': # q[1] == 'filter'
            chk_xpath_expr(ctx, xpath_stmt, initial, node, q[2], None)
            chk_xpath_expr(ctx, xpath_stmt, initial, node, q[3], None)
        elif q[0] == 'var':
            # NOTE: check if the variable is known; currently we don't
            # have any variables in YANG xpath expressions
            pyang.error.err_add(ctx.errors, pos, 'XPATH_VARIABLE', q[1])
        elif q[0] == 'literal':
            # kind of hack to detect qnames, and mark the prefixes
            # as being used in order to avoid warnings.
            s = q[1]
            if s[0] == s[-1] and s[0] in ("'", '"'):
                s = s[1:-1]
                i = s.find(':')
                # make sure there is just one : present
                # FIXME: more colons should possibly be reported, instead
                if i != -1 and s.find(':', i + 1) == -1:
                    prefix = s[:i]
                    tag = s[i + 1:]
                    if (pyang.syntax.re_identifier.search(prefix) is not None and
                        pyang.syntax.re_identifier.search(tag) is not None):
                        # we don't want to report an error; just mark the
                        # prefix as being used.
                        my_errors = []
                        pyang.util.prefix_to_module(mod, prefix, pos, my_errors)
                        for pos0, code, arg in my_errors:
                            if code == 'PREFIX_NOT_DEFINED' and t == 'qstring':
                                # we know for sure that this is an error
                                pyang.error.err_add(ctx.errors, pos0,
                                        'PREFIX_NOT_DEFINED', arg)
                            else:
                                # this may or may not be an error;
                                # report a warning
                                pyang.error.err_add(ctx.errors, pos0,
                                        'WPREFIX_NOT_DEFINED', arg)
            return s
        elif q[0] == 'string':
            return q[1]
        elif q[0] == 'number':
            return q[1]


def chk_xpath_function(ctx, xpath_stmt, initial, node, func, args):
    mod = xpath_stmt.i_orig_module
    pos = xpath_stmt.pos

    signature = None
    if func in pyang.xpath.core_functions:
        signature = pyang.xpath.core_functions[func]
    elif func in pyang.xpath.yang_xpath_functions:
        signature = pyang.xpath.yang_xpath_functions[func]
    elif mod.i_version != '1' and func in pyang.xpath.yang_1_1_xpath_functions:
        signature = pyang.xpath.yang_1_1_xpath_functions[func]
    elif ctx.strict and func in pyang.xpath.extra_xpath_functions:
        pyang.error.err_add(ctx.errors, pos, 'STRICT_XPATH_FUNCTION', func)
        return None
    elif not ctx.strict and func in pyang.xpath.extra_xpath_functions:
        signature = pyang.xpath.extra_xpath_functions[func]
    if signature is None:
        pyang.error.err_add(ctx.errors, pos, 'XPATH_FUNCTION', func)
        return None
    # check that the number of arguments are correct
    nexp = len(signature[0])
    nargs = len(args)
    if nexp == 0:
        if nargs != 0:
            pyang.error.err_add(ctx.errors, pos, 'XPATH_FUNC_ARGS',
                    (func, nexp, nargs))
    elif signature[0][-1] == '?':
        if nargs != (nexp - 1) and nargs != (nexp - 2):
            pyang.error.err_add(ctx.errors, pos, 'XPATH_FUNC_ARGS',
                    (func, "%s-%s" % (nexp - 2, nexp - 1), nargs))
    elif signature[0][-1] == '*':
        if nargs < (nexp - 1):
            pyang.error.err_add(ctx.errors, pos, 'XPATH_FUNC_ARGS',
                    (func, "at least %s" % (nexp - 1), nargs))
    elif nexp != nargs:
        pyang.error.err_add(ctx.errors, pos, 'XPATH_FUNC_ARGS',
                (func, nexp, nargs))
    # check the arguments - FIXME check type
    i = 0
    args_signature = signature[0][:]
    if func == 'deref':
        arg = args[0]
        tgt = chk_xpath_path(ctx, xpath_stmt, initial, node, arg)
        if tgt is not None:
            if not hasattr(tgt, 'i_leafref_ptr') or tgt.i_leafref_ptr is None:
                # not a leafref;
                type_ = tgt.search_one('type')
                if (type_ is None or
                    not isinstance(type_.i_type_spec,
                                   pyang.types.InstanceIdentifierTypeSpec)):
                    pyang.error.err_add(ctx.errors, pos, 'XPATH_DEREF_TARGET', tgt)
                # tgt = None
                return (signature[1], None, [(args_signature[0], arg)])
        return (signature[1], tgt, [(args_signature[0], arg)])
    elif func == 'current':
        return (signature[1], initial, [])
    else:
        inputs = []
        for arg in args:
            obj = chk_xpath_expr(ctx, xpath_stmt, initial, node, arg, args_signature[i])
            inputs.append((args_signature[i], obj))
            if args_signature[i] == '*':
                args_signature.append('*')
            i = i + 1
        return (signature[1], None, inputs)


def chk_xpath_path(ctx, xpath_stmt, initial, node, path):
    mod = xpath_stmt.i_orig_module
    pos = xpath_stmt.pos

    if len(path) == 0:
        return node
    head = path[0]
    if head == 'relative':
        return chk_xpath_path(ctx, xpath_stmt, initial, node, path[1])
    if head[0] == 'var':
        # check if the variable is known as a node-set
        # currently we don't have any variables, so this fails
        pyang.error.err_add(ctx.errors, pos, 'XPATH_VARIABLE', head[1])
    elif head[0] == 'function_call':
        func = head[1]
        args = head[2]
        (rettype, tgt, inputs) = chk_xpath_function(
            ctx, xpath_stmt, initial, node, func, args)
        if rettype is not None:
            # known function, check that it returns a node set
            if rettype != 'node-set':
                pyang.error.err_add(ctx.errors, pos, 'XPATH_FUNCTION_RET_VAL',
                        (func, 'node-set'))
        if func == 'current':
            return chk_xpath_path(ctx, xpath_stmt, initial, initial, path[1:])
        elif func == 'deref':
            t = None
            if tgt is not None:
                (t, _pos) = tgt.i_leafref_ptr
            return chk_xpath_path(ctx, xpath_stmt, initial, t, path[1:])
    elif head[0] == 'step':
        axis = head[1]
        nodetest = head[2]
        preds = head[3]
        node1 = None
        if axis == 'self':
            node1 = node
            pass
        elif nodetest[0] == 'name':
            prefix = nodetest[1]
            name = nodetest[2]
            if prefix is None:
                if initial is None:
                    pmodule = None
                elif initial.keyword == 'module':
                    pmodule = initial
                else:
                    pmodule = initial.i_module
            else:
                pmodule = pyang.util.prefix_to_module(mod, prefix, pos, ctx.errors)
            # if node and initial are None, it means we're checking an XPath
            # expression when it is defined in a grouping or augment, i.e.,
            # when the full tree is not expanded.  in this case we can't check
            # the paths
            if pmodule is not None and node is not None and initial is not None:
                if axis == 'child':
                    if node == 'root':
                        children = pmodule.i_children
                    else:
                        children = getattr(node, 'i_children', None) or []
                    child = pyang.util.search_data_node(
                        children, pmodule.i_modulename, name)
                    if child is None and node == 'root':
                        pyang.error.err_add(ctx.errors, pos, 'XPATH_NODE_NOT_FOUND2',
                                (pmodule.i_modulename, name, pmodule.arg))
                    elif child is None and node.i_module is not None:
                        pyang.error.err_add(ctx.errors, pos, 'XPATH_NODE_NOT_FOUND1',
                                (pmodule.i_modulename, name,
                                 node.i_module.i_modulename, node.arg))
                    elif child is None:
                        pyang.error.err_add(ctx.errors, pos, 'XPATH_NODE_NOT_FOUND2',
                                (pmodule.i_modulename, name, node.arg))
                    elif (getattr(initial, 'i_config', None) is True
                          and getattr(child, 'i_config', None) is False):
                        pyang.error.err_add(ctx.errors, pos, 'XPATH_REF_CONFIG_FALSE',
                                (pmodule.i_modulename, name))
                    else:
                        node1 = child
                elif axis == 'ancestor' or axis == 'ancestor-or-self':
                    p = node
                    if axis == 'ancestor':
                        if node == 'root':
                            pyang.error.err_add(ctx.errors, pos, 'XPATH_ANCESTOR_NOT_FOUND',
                                    (pmodule.i_modulename, name,
                                     node.i_module.i_modulename, node.arg))
                        else:
                            p = pyang.util.data_node_up(node)
                    while (p is not None and
                           not(p.arg == name and
                               p.i_module and
                               p.i_module.i_modulename == pmodule.i_modulename)):
                        p = pyang.util.data_node_up(p)
                    if p is None:
                        pyang.error.err_add(
                            ctx.errors, pos, 'XPATH_ANCESTOR_NOT_FOUND', (
                                pmodule.i_modulename, name,
                                node.i_module.i_modulename, node.arg))
                    else:
                        node1 = p
                        # we have now found one matching ancestor.
                        # NOTE: we don't handle multiple matching ancestors,
                        # so we check for this
                        p = pyang.util.data_node_up(p)
                        while (p is not None and
                               not(p.arg == name and
                                   p.i_module and
                                   p.i_module.i_modulename ==
                                   pmodule.i_modulename)):
                            p = pyang.util.data_node_up(p)
                        if p is not None:
                            # multiple ancestors; give a warning and continue
                            pyang.error.err_add(
                                ctx.errors, pos, 'XPATH_MULTIPLE_ANCESTORS', (
                                    node.i_module.i_modulename, node.arg,
                                    pmodule.i_modulename, name))
                            node1 = None
                else:
                    # we can't validate the steps on other axis, but we can
                    # validate functions etc.
                    pass
        elif axis == 'parent' and nodetest == ('node_type', 'node'):
            if node is None:
                pass
            elif node == 'root':
                pyang.error.err_add(ctx.errors, pos, 'XPATH_PATH_TOO_MANY_UP', ())
            else:
                p = pyang.util.data_node_up(node)
                if p is None:
                    pyang.error.err_add(ctx.errors, pos, 'XPATH_PATH_TOO_MANY_UP', ())
                else:
                    node1 = p
        else:
            # we can't validate the steps on other axis, but we can
            # validate functions etc.
            pass
        for p in preds:
            chk_xpath_expr(ctx, xpath_stmt, initial, node1, p, None)

        return chk_xpath_path(ctx, xpath_stmt, initial, node1, path[1:])

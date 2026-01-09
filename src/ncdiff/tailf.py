import logging
from os import path
from lxml import etree
from pyang import util

from .composer import Tag

logger = logging.getLogger(__name__)


def has_tailf_ordering(stmt, context):
    prefix, identifier = stmt.raw_keyword
    m, rev = util.prefix_to_modulename_and_revision(
        stmt.i_orig_module,
        prefix,
        stmt.pos,
        context.errors,
    )
    return m == 'tailf-common' and identifier in {
        'cli-diff-after', 'cli-diff-before',
        'cli-diff-create-after', 'cli-diff-create-before',
        'cli-diff-delete-after', 'cli-diff-delete-before',
        'cli-diff-modify-after', 'cli-diff-modify-before',
        'cli-diff-set-after', 'cli-diff-set-before',
        'cli-diff-dependency',
    }


def get_tailf_ordering(context, stmt, target_stmt):
    symmetric = is_symmetric_tailf_ordering(context, stmt, target_stmt)
    if stmt.keyword[1] in ['cli-diff-after', 'cli-diff-before']:
        conj = 'after' if stmt.keyword[1] == 'cli-diff-after' else 'before'
        valid_substmts = {
            'cli-when-target-set',
            'cli-when-target-create',
            'cli-when-target-modify',
            'cli-when-target-delete',
        }
        substmts = [s for s in stmt.substmts if s.keyword[1] in valid_substmts]
        if len(substmts) == 0:
            return {
                ('create', conj, 'create'),
                ('modify', conj, 'create'),
                ('delete', conj, 'create'),
                ('create', conj, 'modify'),
                ('modify', conj, 'modify'),
                ('delete', conj, 'modify'),
                ('create', conj, 'delete'),
                ('modify', conj, 'delete'),
                ('delete', conj, 'delete'),
            }
        ordering = set()
        for substmt in substmts:
            if substmt.keyword[1] == 'cli-when-target-set':
                ordering.update({
                    ('create', conj, 'create'),
                    ('modify', conj, 'create'),
                    ('delete', conj, 'create'),
                    ('create', conj, 'modify'),
                    ('modify', conj, 'modify'),
                    ('delete', conj, 'modify'),
                })
            elif substmt.keyword[1] == 'cli-when-target-create':
                ordering.update({
                    ('create', conj, 'create'),
                    ('modify', conj, 'create'),
                    ('delete', conj, 'create'),
                })
            elif substmt.keyword[1] == 'cli-when-target-modify':
                ordering.update({
                    ('create', conj, 'modify'),
                    ('modify', conj, 'modify'),
                    ('delete', conj, 'modify'),
                })
            elif substmt.keyword[1] == 'cli-when-target-delete':
                ordering.update({
                    ('create', conj, 'delete'),
                    ('modify', conj, 'delete'),
                    ('delete', conj, 'delete'),
                })
        return ordering
    elif stmt.keyword[1] in ['cli-diff-create-after', 'cli-diff-create-before']:
        conj = 'after' if stmt.keyword[1] == 'cli-diff-create-after' else 'before'
        valid_substmts = {
            'cli-when-target-set',
            'cli-when-target-create',
            'cli-when-target-modify',
            'cli-when-target-delete',
        }
        substmts = [s for s in stmt.substmts if s.keyword[1] in valid_substmts]
        if len(substmts) == 0:
            if symmetric:
                return {
                    ('create', conj, 'modify'),
                    ('create', conj, 'delete'),
                }
            else:
                return {
                    ('create', conj, 'create'),
                    ('create', conj, 'modify'),
                    ('create', conj, 'delete'),
                }
        ordering = set()
        for substmt in substmts:
            if substmt.keyword[1] == 'cli-when-target-set':
                ordering.update({
                    ('create', conj, 'create'),
                    ('create', conj, 'modify'),
                })
            elif substmt.keyword[1] == 'cli-when-target-create':
                ordering.add(
                    ('create', conj, 'create'),
                )
            elif substmt.keyword[1] == 'cli-when-target-modify':
                ordering.add(
                    ('create', conj, 'modify'),
                )
            elif substmt.keyword[1] == 'cli-when-target-delete':
                ordering.add(
                    ('create', conj, 'delete'),
                )
        return ordering
    elif stmt.keyword[1] in ['cli-diff-delete-after', 'cli-diff-delete-before']:
        conj = 'after' if stmt.keyword[1] == 'cli-diff-delete-after' else 'before'
        valid_substmts = {
            'cli-when-target-set',
            'cli-when-target-create',
            'cli-when-target-modify',
            'cli-when-target-delete',
        }
        substmts = [s for s in stmt.substmts if s.keyword[1] in valid_substmts]
        if len(substmts) == 0:
            if symmetric:
                return {
                    ('delete', conj, 'create'),
                    ('delete', conj, 'modify'),
                }
            else:
                return {
                    ('delete', conj, 'create'),
                    ('delete', conj, 'modify'),
                    ('delete', conj, 'delete'),
                }
        ordering = set()
        for substmt in substmts:
            if substmt.keyword[1] == 'cli-when-target-set':
                ordering.update({
                    ('delete', conj, 'create'),
                    ('delete', conj, 'modify'),
                })
            elif substmt.keyword[1] == 'cli-when-target-create':
                ordering.add(
                    ('delete', conj, 'create'),
                )
            elif substmt.keyword[1] == 'cli-when-target-modify':
                ordering.add(
                    ('delete', conj, 'modify'),
                )
            elif substmt.keyword[1] == 'cli-when-target-delete':
                ordering.add(
                    ('delete', conj, 'delete'),
                )
        return ordering
    elif stmt.keyword[1] in ['cli-diff-modify-after', 'cli-diff-modify-before']:
        conj = 'after' if stmt.keyword[1] == 'cli-diff-modify-after' else 'before'
        valid_substmts = {
            'cli-when-target-set',
            'cli-when-target-create',
            'cli-when-target-modify',
            'cli-when-target-delete',
        }
        substmts = [s for s in stmt.substmts if s.keyword[1] in valid_substmts]
        if len(substmts) == 0:
            return {
                ('modify', conj, 'create'),
                ('modify', conj, 'modify'),
                ('modify', conj, 'delete'),
            }
        ordering = set()
        for substmt in substmts:
            if substmt.keyword[1] == 'cli-when-target-set':
                ordering.update({
                    ('modify', conj, 'create'),
                    ('modify', conj, 'modify'),
                })
            elif substmt.keyword[1] == 'cli-when-target-create':
                ordering.add(
                    ('modify', conj, 'create'),
                )
            elif substmt.keyword[1] == 'cli-when-target-modify':
                ordering.add(
                    ('modify', conj, 'modify'),
                )
            elif substmt.keyword[1] == 'cli-when-target-delete':
                ordering.add(
                    ('modify', conj, 'delete'),
                )
        return ordering
    elif stmt.keyword[1] in ['cli-diff-set-after', 'cli-diff-set-before']:
        conj = 'after' if stmt.keyword[1] == 'cli-diff-set-after' else 'before'
        valid_substmts = {
            'cli-when-target-set',
            'cli-when-target-create',
            'cli-when-target-modify',
            'cli-when-target-delete',
        }
        substmts = [s for s in stmt.substmts if s.keyword[1] in valid_substmts]
        if len(substmts) == 0:
            return {
                ('create', conj, 'create'),
                ('modify', conj, 'create'),
                ('create', conj, 'modify'),
                ('modify', conj, 'modify'),
                ('create', conj, 'delete'),
                ('modify', conj, 'delete'),
            }
        ordering = set()
        for substmt in substmts:
            if substmt.keyword[1] == 'cli-when-target-set':
                ordering.update({
                    ('create', conj, 'create'),
                    ('modify', conj, 'create'),
                    ('create', conj, 'modify'),
                    ('modify', conj, 'modify'),
                })
            elif substmt.keyword[1] == 'cli-when-target-create':
                ordering.update({
                    ('create', conj, 'create'),
                    ('modify', conj, 'create'),
                })
            elif substmt.keyword[1] == 'cli-when-target-modify':
                ordering.update({
                    ('create', conj, 'modify'),
                    ('modify', conj, 'modify'),
                })
            elif substmt.keyword[1] == 'cli-when-target-delete':
                ordering.update({
                    ('create', conj, 'delete'),
                    ('modify', conj, 'delete'),
                })
        return ordering
    elif stmt.keyword[1] == 'cli-diff-dependency':
        valid_substmts = {
            'cli-trigger-on-set',
            'cli-trigger-on-delete',
            'cli-trigger-on-all',
        }
        substmts = [s for s in stmt.substmts if s.keyword[1] in valid_substmts]
        ordering = {
            ('create', 'after', 'create'),
            ('modify', 'after', 'create'),
            ('delete', 'before', 'modify'),
            ('create', 'before', 'delete'),
            ('modify', 'before', 'delete'),
            ('delete', 'before', 'delete'),
        }
        # Test result from TailF confd 8.4.7.1:
        # 1 depends on 2
        # ('create', 'after', 'create'),
        # ('modify', 'after', 'create'),
        # ('delete', 'before', 'create'),
        # ('create', 'before', 'modify'),
        # ('modify', 'before', 'modify'),
        # ('delete', 'before', 'modify'),
        # ('create', 'before', 'delete'),
        # ('modify', 'before', 'delete'),
        # ('delete', 'before', 'delete'),
        # 2 depends on 1
        # ('create', 'after', 'create'),
        # ('modify', 'after', 'create'),
        # ('delete', 'after', 'create'),
        # ('create', 'after', 'modify'),
        # ('modify', 'after', 'modify'),
        # ('delete', 'before', 'modify'),
        # ('create', 'before', 'delete'),
        # ('modify', 'before', 'delete'),
        # ('delete', 'before', 'delete'),
        if len(substmts) == 0:
            return ordering
        ordering = set()
        for substmt in substmts:
            if substmt.keyword[1] == 'cli-trigger-on-set':
                ordering.update({
                    ('create', 'after', 'create'),
                    ('modify', 'after', 'create'),
                    ('create', 'after', 'modify'),
                    ('modify', 'after', 'modify'),
                })
                # Test result from TailF confd 8.4.7.1:
                # 1 depends on 2
                # ('create', 'after', 'create'),
                # ('modify', 'after', 'create'),
                # ('delete', 'before', 'create'),
                # ('create', 'after', 'modify'),
                # ('modify', 'after', 'modify'),
                # ('delete', 'before', 'modify'),
                # ('create', 'after', 'delete'),
                # ('modify', 'after', 'delete'),
                # ('delete', 'before', 'delete'),
                # 2 depends on 1
                # ('create', 'after', 'create'),
                # ('modify', 'after', 'create'),
                # ('delete', 'after', 'create'),
                # ('create', 'after', 'modify'),
                # ('modify', 'after', 'modify'),
                # ('delete', 'after', 'modify'),
                # ('create', 'after', 'delete'),
                # ('modify', 'after', 'delete'),
                # ('delete', 'after', 'delete'),
            elif substmt.keyword[1] == 'cli-trigger-on-delete':
                ordering.update({
                    ('create', 'after', 'create'),
                    ('modify', 'after', 'create'),
                    ('delete', 'before', 'modify'),
                    ('delete', 'before', 'delete'),
                })
                # Test result from TailF confd 8.4.7.1:
                # 1 depends on 2
                # ('create', 'after', 'create'),
                # ('modify', 'after', 'create'),
                # ('delete', 'before', 'create'),
                # ('create', 'before', 'modify'),
                # ('modify', 'before', 'modify'),
                # ('delete', 'before', 'modify'),
                # ('create', 'before', 'delete'),
                # ('modify', 'before', 'delete'),
                # ('delete', 'before', 'delete'),
                # 2 depends on 1
                # ('create', 'after', 'create'),
                # ('modify', 'after', 'create'),
                # ('delete', 'after', 'create'),
                # ('create', 'after', 'modify'),
                # ('modify', 'after', 'modify'),
                # ('delete', 'before', 'modify'),
                # ('create', 'before', 'delete'),
                # ('modify', 'before', 'delete'),
                # ('delete', 'before', 'delete'),
            elif substmt.keyword[1] == 'cli-trigger-on-all':
                return {
                    ('create', 'after', 'create'),
                    ('modify', 'after', 'create'),
                    ('delete', 'after', 'create'),
                    ('create', 'after', 'modify'),
                    ('modify', 'after', 'modify'),
                    ('delete', 'after', 'modify'),
                    ('create', 'after', 'delete'),
                    ('modify', 'after', 'delete'),
                    ('delete', 'after', 'delete'),
                }
                # Test result from TailF confd 8.4.7.1:
                # 1 depends on 2
                # ('create', 'after', 'create'),
                # ('modify', 'after', 'create'),
                # ('delete', 'after', 'create'),
                # ('create', 'after', 'modify'),
                # ('modify', 'after', 'modify'),
                # ('delete', 'after', 'modify'),
                # ('create', 'after', 'delete'),
                # ('modify', 'after', 'delete'),
                # ('delete', 'after', 'delete'),
                # 2 depends on 1
                # ('create', 'after', 'create'),
                # ('modify', 'after', 'create'),
                # ('delete', 'after', 'create'),
                # ('create', 'after', 'modify'),
                # ('modify', 'after', 'modify'),
                # ('delete', 'after', 'modify'),
                # ('create', 'after', 'delete'),
                # ('modify', 'after', 'delete'),
                # ('delete', 'after', 'delete'),
        return ordering
    return set()

def add_tailf_annotation(module_namespaces, stmt, node):
    if len(stmt.substmts) > 0:
        sub_sm_dict = {
            sub.keyword[1]: sub.arg if sub.arg is not None else ''
            for sub in stmt.substmts
            if (
                isinstance(sub.keyword, tuple) and
                'tailf' in sub.keyword[0]
            )
        }
        node.set(
            etree.QName(module_namespaces[stmt.keyword[0]],
                        stmt.keyword[1]),
            repr(sub_sm_dict) if sub_sm_dict else '',
        )
    else:
        node.set(
            etree.QName(module_namespaces[stmt.keyword[0]],
                        stmt.keyword[1]),
            stmt.arg if stmt.arg else '',
        )


def set_ordering_xpath(compiler, module):
    for constraint_type in ["ordering_stmt_leafref", "ordering_stmt_tailf"]:
        if (
            hasattr(compiler, constraint_type) and
            module in getattr(compiler, constraint_type)
        ):
            constraints = write_ordering_xpath(
                compiler, module, constraint_type)


def write_ordering_xpath(compiler, module, constraint_type):

    def get_xpath(compiler, stmt):
        schema_node = getattr(stmt, 'schema_node', None)
        if schema_node is None:
            return ''
        if not hasattr(stmt, 'schema_xpath'):
            stmt.schema_xpath = compiler.get_xpath_from_schema_node(
                schema_node, type=Tag.LXML_XPATH)
        return stmt.schema_xpath

    constraints = []
    stmt = {}
    xpath = {}
    constraint_info = getattr(compiler, constraint_type)[module]
    for stmt[0], stmt[1] in constraint_info:
        for i in range(2):
            xpath[i] = get_xpath(compiler, stmt[i])
        if xpath[0] == '' or xpath[1] == '':
            # Skip entries with missing Xpath. Missing Xpaths might be in a
            # different module not compiled or due to other deviations.
            continue
        cinstraint_list, pos = constraint_info[(stmt[0], stmt[1])]
        for oper_0, sequence, oper_1 in cinstraint_list:
            if xpath[0] == xpath[1] and oper_0 == oper_1:
                # Skip entries with same Xpath and same operation.
                continue
            if sequence == 'before':
                constraints.append((
                    f"{xpath[0]}, {oper_0}", f"{xpath[1]}, {oper_1}", pos))
                update_schema_tree(stmt[0], oper_0, stmt[1], oper_1)
            else:
                constraints.append((
                    f"{xpath[1]}, {oper_1}", f"{xpath[0]}, {oper_0}", pos))
                update_schema_tree(stmt[1], oper_1, stmt[0], oper_0)

    attribute_name = "ordering_xpath_leafref" \
        if constraint_type == "ordering_stmt_leafref" \
        else "ordering_xpath_tailf"
    getattr(compiler, attribute_name)[module] = constraints
    if len(constraints) > 0:
        csv_filename = path.join(
            compiler.dir_yang, f'{module}_{attribute_name}.csv')
        with open(csv_filename, 'w') as f:
            f.write("\n".join([f"{c[0]}, {c[1]}" for c in constraints]))

    return [(c[0], c[1]) for c in constraints]


def update_schema_tree(stmt_0, oper_0, stmt_1, oper_1):
    schema_node_1 = getattr(stmt_0, 'schema_node', None)
    if schema_node_1 is None:
        logger.warning(
            f"Schema node not found for statement {stmt_0.keyword} "
            f"at {stmt_0.pos}")
        return
    ordering_str = schema_node_1.get("before")
    if ordering_str is None:
        schema_node_1.set("before", repr({
            oper_0: {stmt_1.schema_xpath: [oper_1]}
        }))
    else:
        ordering = eval(ordering_str)
        if oper_0 in ordering:
            if stmt_1.schema_xpath in ordering[oper_0]:
                if oper_1 in ordering[oper_0][stmt_1.schema_xpath]:
                    return
                else:
                    ordering[oper_0][stmt_1.schema_xpath].append(oper_1)
            else:
                ordering[oper_0][stmt_1.schema_xpath] = [oper_1]
        else:
            ordering[oper_0] = {stmt_1.schema_xpath: [oper_1]}
        schema_node_1.set("before", repr(ordering))


def is_symmetric_tailf_ordering(context, stmt, target_stmt):
    if len(stmt.substmts) != 0:
        return False
    substmts = {
        s for s in target_stmt.substmts
        if isinstance(s.keyword, tuple) and
        'tailf' in s.keyword[0] and
        len(s.substmts) == 0 and
        s.keyword[1] == stmt.keyword[1]
    }
    for substmt in substmts:
        target = context.check_data_tree_xpath(
            substmt, target_stmt)
        if target == stmt.parent:
            return True
    return False

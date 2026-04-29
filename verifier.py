import streamlit as st
import re
import streamlit_antd_components as sac
from collections import defaultdict

############################################################
# AST NODE
############################################################

class ASTNode:
    def __init__(self, node_type, value=None, file=None):
        self.type = node_type
        self.value = value
        self.file = file
        self.children = []

    def add(self, node):
        self.children.append(node)

############################################################
# CLEAN COMMENTS
############################################################

def remove_comments(text):
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)

############################################################
# TOKENIZER
############################################################

def tokenize(text):
    return [l.strip() for l in text.splitlines() if l.strip()]

############################################################
# TCL PARSER
############################################################

def parse_tcl_content(content, filename):

    content = remove_comments(content)
    tokens = tokenize(content)

    root = ASTNode("FILE", filename)

    stack = []
    current = root

    for line in tokens:

        if line.startswith("INCLUDE"):
            current.add(ASTNode("INCLUDE", line.split()[1], filename))

        elif line.startswith("PROC"):
            name = line.replace("PROC","").replace(";","").strip()
            node = ASTNode("PROC", name, filename)
            current.add(node)
            stack.append(current)
            current = node

        elif line.startswith("SUBR"):
            name = line.replace("SUBR","").strip()
            node = ASTNode("SUBR", name, filename)
            current.add(node)
            stack.append(current)
            current = node

        elif re.match(r"\d+:", line):
            step = line.split(":")[0]
            node = ASTNode("STEP", step, filename)
            current.add(node)
            stack.append(current)
            current = node

        elif line.startswith("BEGIN"):
            node = ASTNode("BEGIN")
            current.add(node)
            stack.append(current)
            current = node

        elif line.startswith("END"):
            if stack:
                current = stack.pop()

        elif line.startswith(("VAR","VARTAG","DBVAR","UNITS")):
            current.add(ASTNode("DECL", line))

        else:
            current.add(ASTNode("COMMAND", line))

    return root

############################################################
# BUILD PROJECT AST
############################################################

def build_project_ast(files):

    project = ASTNode("PROJECT")

    for f in files:
        content = f.read().decode(errors="ignore")
        project.add(parse_tcl_content(content, f.name))

    return project

############################################################
# SYMBOL TABLE
############################################################

def build_symbol_table(project):

    symbols = {}

    for file in project.children:
        for node in file.children:
            if node.type in ["PROC","SUBR"]:
                symbols[node.value] = node

    return symbols

############################################################
# INCLUDE RESOLUTION (MERGING)
############################################################

def resolve_includes(project, symbols):

    for file in project.children:

        new_nodes = []

        for node in file.children:

            if node.type == "INCLUDE":

                name = node.value.replace(";","")

                if name in symbols:
                    new_nodes.extend(symbols[name].children)

            else:
                new_nodes.append(node)

        file.children = new_nodes

############################################################
# MERGE PROGRAM
############################################################

def merge_program(project):

    merged = ASTNode("MERGED_PROGRAM")

    seen = set()

    for file in project.children:
        for node in file.children:

            key = (node.type, node.value)

            if key not in seen:
                merged.add(node)
                seen.add(key)

    return merged

############################################################
# CALL GRAPH BUILDER
############################################################

def build_call_graph(root, symbols):

    calls = defaultdict(set)

    def visit(node, current_proc=None):

        if node.type in ["PROC","SUBR"]:
            current_proc = node.value

        if node.type == "COMMAND":
            for name in symbols:
                if name in node.value:
                    calls[current_proc].add(name)

        for c in node.children:
            visit(c, current_proc)

    visit(root)
    return calls

############################################################
# EXECUTION FLOW (STEP CFG)
############################################################

def build_execution_flow(root):

    edges = []

    steps = []

    def visit(node):
        if node.type == "STEP":
            steps.append(node.value)

        for c in node.children:
            visit(c)

    visit(root)

    for i in range(len(steps)-1):
        edges.append((steps[i], steps[i+1]))

    return edges

############################################################
# SIMPLE VERIFICATION CHECKS
############################################################

def run_verification(call_graph, steps):

    issues = []

    # recursive calls
    for caller, callees in call_graph.items():
        if caller in callees:
            issues.append(f"Recursive call detected in {caller}")

    # missing start step
    if "1" not in [s[0] for s in steps]:
        issues.append("No STEP 1 detected")

    return issues

############################################################
# AST → TREE
############################################################

def ast_to_tree(node):

    label = node.type if node.value is None else f"{node.type}: {node.value}"

    return sac.TreeItem(
        label=label,
        children=[ast_to_tree(c) for c in node.children]
    )

############################################################
# STREAMLIT UI
############################################################

st.set_page_config(layout="wide")
st.title("🚀 TCL Static Analyzer (Unified AST + CFG + Verification)")

files = st.file_uploader(
    "Upload TCL Files",
    type=["tcl"],
    accept_multiple_files=True
)

if files:

    with st.spinner("Analyzing TCL Project..."):

        project = build_project_ast(files)

        symbols = build_symbol_table(project)

        resolve_includes(project, symbols)

        merged = merge_program(project)

        call_graph = build_call_graph(merged, symbols)

        cfg = build_execution_flow(merged)

        issues = run_verification(call_graph, cfg)

    st.success("Analysis Complete")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["AST","Call Graph","Execution Flow","Verification"]
    )

    ########################################################
    # AST VIEW
    ########################################################
    with tab1:
        tree = ast_to_tree(merged)
        sac.tree(items=[tree], height=700)

    ########################################################
    # CALL GRAPH
    ########################################################
    with tab2:
        st.json({k:list(v) for k,v in call_graph.items()})

    ########################################################
    # EXECUTION FLOW
    ########################################################
    with tab3:
        st.write("Step Transitions")
        for e in cfg:
            st.write(f"{e[0]} → {e[1]}")

    ########################################################
    # VERIFICATION
    ########################################################
    with tab4:
        if issues:
            for i in issues:
                st.error(i)
        else:
            st.success("No verification issues detected")

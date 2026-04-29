import streamlit as st
import re
import streamlit_antd_components as sac

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
# TOKENIZE
############################################################

def tokenize(text):
    return [l.strip() for l in text.splitlines() if l.strip()]

############################################################
# PARSER
############################################################

def parse_tcl_content(content, filename):

    content = remove_comments(content)
    tokens = tokenize(content)

    root = ASTNode("FILE", filename)

    current_block = root
    stack = []

    for line in tokens:

        if line.startswith("INCLUDE"):
            node = ASTNode("INCLUDE", line.split()[1], filename)
            current_block.add(node)

        elif line.startswith("PROC"):
            name = line.replace("PROC", "").replace(";", "").strip()
            node = ASTNode("PROC", name, filename)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        elif line.startswith("SUBR"):
            name = line.replace("SUBR", "").strip()
            node = ASTNode("SUBR", name, filename)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        elif re.match(r"\d+:", line):
            step = line.split(":")[0]
            node = ASTNode("STEP_LABEL", step, filename)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        elif line.startswith("STEP"):
            node = ASTNode("STEP", line)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        elif line.startswith("BEGIN"):
            node = ASTNode("BEGIN")
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        elif line.startswith("END"):
            if stack:
                current_block = stack.pop()

        elif line.startswith(("VAR","VARTAG","DBVAR","UNITS")):
            current_block.add(ASTNode("DECL_SECTION", line))

        else:
            current_block.add(ASTNode("COMMAND", line))

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
                symbols[node.value] = node.file

    return symbols

############################################################
# AST → TREE DATA (Visualization)
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

st.title("🌳 ABB TCL Unified AST Visualizer")

uploaded_files = st.file_uploader(
    "Upload Multiple TCL Files",
    type=["tcl"],
    accept_multiple_files=True
)

if uploaded_files:

    with st.spinner("Building Unified AST..."):
        project_ast = build_project_ast(uploaded_files)
        symbols = build_symbol_table(project_ast)

    st.success("AST Generated")

    col1, col2 = st.columns([1,3])

    ########################################################
    # SYMBOL TABLE
    ########################################################
    with col1:
        st.subheader("Procedures / Subroutines")
        st.json(symbols)

    ########################################################
    # TREE VISUALIZATION
    ########################################################
    with col2:

        st.subheader("AST Tree")

        tree_data = ast_to_tree(project_ast)

        sac.tree(
            items=[tree_data],
            open_all=False,
            checkbox=False,
            show_line=True,
            height=700
        )

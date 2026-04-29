import streamlit as st
import os
import re

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
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return text

############################################################
# LEXER
############################################################

def tokenize(text):

    tokens = []

    for line in text.splitlines():

        line = line.strip()

        if not line:
            continue

        tokens.append(line)

    return tokens

############################################################
# TCL DSL PARSER (ABB STYLE)
############################################################

def parse_tcl_file(path):

    with open(path, "r", errors="ignore") as f:
        content = remove_comments(f.read())

    tokens = tokenize(content)

    root = ASTNode("FILE", path)

    current_block = root

    stack = []

    for line in tokens:

        ########################################
        # INCLUDE
        ########################################
        if line.startswith("INCLUDE"):
            node = ASTNode("INCLUDE", line.split()[1], path)
            current_block.add(node)

        ########################################
        # PROC
        ########################################
        elif line.startswith("PROC"):
            name = line.replace("PROC", "").replace(";", "").strip()
            node = ASTNode("PROC", name, path)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        ########################################
        # SUBR
        ########################################
        elif line.startswith("SUBR"):
            name = line.replace("SUBR", "").strip()
            node = ASTNode("SUBR", name, path)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        ########################################
        # STEP LABEL
        ########################################
        elif re.match(r"\d+:", line):
            step_id = line.split(":")[0]
            node = ASTNode("STEP_LABEL", step_id, path)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        ########################################
        # STEP BLOCK
        ########################################
        elif line.startswith("STEP"):
            node = ASTNode("STEP", line, path)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        ########################################
        # BEGIN BLOCK
        ########################################
        elif line.startswith("BEGIN"):
            node = ASTNode("BEGIN", None, path)
            current_block.add(node)
            stack.append(current_block)
            current_block = node

        ########################################
        # END BLOCK
        ########################################
        elif line.startswith("END"):
            if stack:
                current_block = stack.pop()

        ########################################
        # VARIABLE SECTIONS
        ########################################
        elif line.startswith(("VAR", "VARTAG", "DBVAR", "UNITS")):
            node = ASTNode("DECL_SECTION", line, path)
            current_block.add(node)

        ########################################
        # COMMAND
        ########################################
        else:
            node = ASTNode("COMMAND", line, path)
            current_block.add(node)

    return root


############################################################
# MERGE MULTIPLE FILES → SINGLE AST
############################################################

def build_project_ast(folder):

    project = ASTNode("PROJECT")

    for file in os.listdir(folder):

        if file.lower().endswith(".tcl"):

            path = os.path.join(folder, file)

            ast = parse_tcl_file(path)

            project.add(ast)

    return project


############################################################
# AST VISUALIZER
############################################################

def show_ast(node, level=0):

    st.text("  " * level + f"{node.type}: {node.value}")

    for c in node.children:
        show_ast(c, level + 1)


############################################################
# SYMBOL TABLE (GLOBAL)
############################################################

def build_symbol_table(project):

    symbols = {}

    for file in project.children:

        for node in file.children:

            if node.type in ["PROC", "SUBR"]:
                symbols[node.value] = node.file

    return symbols


############################################################
# STREAMLIT UI
############################################################

st.title("ABB AdvaBuild TCL → Unified AST Generator")

folder = st.text_input("TCL Folder Path")

if st.button("Generate Project AST"):

    if not os.path.exists(folder):
        st.error("Folder not found")
    else:

        project_ast = build_project_ast(folder)

        symbols = build_symbol_table(project_ast)

        st.success("Unified AST Created")

        st.subheader("Detected Procedures / Subroutines")
        st.write(symbols)

        st.subheader("AST View")
        show_ast(project_ast)

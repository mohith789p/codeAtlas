from app.schemas.files import FileNode


def build_file_tree(filepaths: list[str]) -> list[FileNode]:
    """Transform flat relative filepaths into a sorted nested FileNode tree."""
    if not filepaths:
        return []

    root_children: list[FileNode] = []
    dirs_by_path: dict[str, FileNode] = {}

    def get_or_create_dir(dir_path: str) -> FileNode:
        if dir_path in dirs_by_path:
            return dirs_by_path[dir_path]
        parts = dir_path.split("/")
        name = parts[-1]
        parent_dir_path = "/".join(parts[:-1]) if len(parts) > 1 else ""

        node = FileNode(name=name, path=dir_path, type="directory", children=[])
        dirs_by_path[dir_path] = node

        if parent_dir_path:
            parent_node = get_or_create_dir(parent_dir_path)
            parent_node.children.append(node)
        else:
            root_children.append(node)
        return node

    for fp in filepaths:
        parts = fp.split("/")
        if len(parts) == 1:
            root_children.append(FileNode(name=parts[0], path=fp, type="file"))
        else:
            dir_path = "/".join(parts[:-1])
            parent_node = get_or_create_dir(dir_path)
            parent_node.children.append(FileNode(name=parts[-1], path=fp, type="file"))

    def sort_nodes(nodes: list[FileNode]) -> list[FileNode]:
        dirs = sorted([n for n in nodes if n.type == "directory"], key=lambda n: n.name.lower())
        files = sorted([n for n in nodes if n.type != "directory"], key=lambda n: n.name.lower())
        for d in dirs:
            if d.children:
                d.children = sort_nodes(d.children)
        return dirs + files

    return sort_nodes(root_children)

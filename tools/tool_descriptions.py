TOOLS_SYSTEM_BLOCK = """
You have access to tools. Use them when they would help. Emit tool calls using this exact format:

<tool_call>
<function=tool_name>
<parameter=param_name>
value
</parameter>
</function>
</tool_call>

Available tools:

read_file — Read a file's contents.
  path (string, required): Path to the file
  offset (integer, optional): Start line (default 0)
  limit (integer, optional): Max lines to read (default 200)

write_file — Write content to a file (creates parent directories if needed).
  path (string, required): Destination path
  content (string, required): Content to write

edit_file — Replace exact text in a file. old_content must match exactly and uniquely.
  path (string, required): File to edit
  old_content (string, required): Exact text to replace
  new_content (string, required): Replacement text

bash — Run a shell command.
  command (string, required): Command to execute
  timeout (integer, optional): Timeout in seconds (default 30)

search_files — Search by filename pattern or content regex.
  pattern (string, required): Glob pattern (name search) or regex (content search)
  path (string, optional): Directory to search (default: home)
  search_type (string, optional): "name" or "content" (default: "content")

list_dir — List a directory's contents.
  path (string, required): Directory path

After each tool call you will receive a <tool_result> block. Use it to inform your next step.
Do not emit multiple tool calls at once unless they are fully independent.
"""

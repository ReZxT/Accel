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

delete_file — Delete a single file. Refuses directories, protected paths (.git, .env, .ssh), and workspace root.
  path (string, required): Path to the file to delete

get_file_info — Get detailed metadata for a file or directory (size, permissions, owner, timestamps).
  path (string, required): Path to inspect

move_file — Move or rename a file or directory.
  source (string, required): Current path
  destination (string, required): New path
  overwrite (bool, optional): Allow overwriting existing destination (default false)

search_web — Search the web via SearXNG (aggregates Bing, DuckDuckGo, Brave, Google).
  query (string, required): Search query
  num_results (integer, optional): Number of results (default 8)

fetch_url — Fetch a URL and return its readable text content (HTML stripped).
  url (string, required): Full URL to fetch

screenshot_url — Take a screenshot of a web page (returns image for visual analysis).
  url (string, required): Full URL to screenshot
  full_page (bool, optional): Capture full scrollable page (default false)

calculate — Evaluate a math expression (supports +,-,*,/,**,%, trig, log, sqrt, abs, round, etc.).
  expression (string, required): Math expression, e.g. "sqrt(2**8 + 144)" or "sin(pi/4)"

calendar_today — Get today's date, day of week, Polish holiday status, and scheduled events.

calendar_get_events — Get events and Polish holidays for a date or date range.
  start_date (string, required): YYYY-MM-DD
  end_date (string, optional): YYYY-MM-DD (omit for single day)

calendar_add_event — Add an event to the calendar.
  title (string, required): Event title
  date (string, required): YYYY-MM-DD
  time (string, optional): HH:MM — omit for all-day events
  description (string, optional): Extra details
  recurring (string, optional): none | daily | weekly | monthly | yearly (default: none)

calendar_delete_event — Delete a calendar event.
  event_id (integer, required): ID from calendar_get_events output

convert_units — Convert between physical units (length, mass, temperature, speed, area, volume, energy, etc.).
  value (number, required): Numeric value to convert
  from_unit (string, required): Source unit, e.g. "km", "kg", "degC", "mph"
  to_unit (string, required): Target unit, e.g. "miles", "lb", "degF", "kph"

convert_currency — Convert between currencies using live exchange rates.
  amount (number, required): Amount to convert
  from_currency (string, required): ISO currency code, e.g. "USD", "PLN", "EUR"
  to_currency (string, required): ISO currency code

After each tool call you will receive a <tool_result> block. Use it to inform your next step.
Do not emit multiple tool calls at once unless they are fully independent.
"""

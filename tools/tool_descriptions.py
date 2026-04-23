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

search_knowledge_base — Semantically search ingested books and documents (PDFs, EPUBs, papers). Use this before searching the web when the user asks about topics that may be in their library.
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)

list_knowledge_base — List all books and documents currently ingested in the knowledge base.

delete_source — Delete a document and all its chunks from the knowledge base. Use list_knowledge_base first to confirm the exact title. Requires approval.
  title (string, required): Exact title of the document to delete

delete_note — Delete a note and all its chunks from the notes collection. Use list_notes first to confirm the exact title. Requires approval.
  title (string, required): Exact title of the note to delete

search_notes — Semantically search the Obsidian vault notes.
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)

list_notes — List all notes currently indexed in the notes collection.

ingest_note — Ingest or re-ingest a local markdown file into the notes collection. Use this after editing a note with edit_file or write_file so the updated content is searchable.
  path (string, required): Path to the markdown file
  title (string, optional): Override the note title

save_memory — Save a piece of information directly to memory, bypassing the curator. Deduplication is automatic — exact duplicates are silently skipped.
  text (string, required): The information to save
  collection (string, optional): Target collection — facts (default), procedures, or episodes

update_memory — Replace an existing memory item with corrected or updated text. Use search_facts/search_procedures/search_episodes first to retrieve the exact stored text, then pass it as old_text. Deletes the old entry and inserts the new one.
  old_text (string, required): Exact text of the existing entry to replace
  new_text (string, required): Updated text to store instead
  collection (string, optional): Collection to update — facts (default), procedures, or episodes

delete_memory — Delete an exact memory entry. Use search_facts/search_procedures/search_episodes first to find the exact stored text, then pass it here.
  text (string, required): Exact text of the entry to delete
  collection (string, optional): Collection to delete from — facts (default), procedures, or episodes

  text (string, required): The information to save
  collection (string, optional): Target collection — facts (default), procedures, or episodes

search_facts — Search the facts memory collection for stored facts about the user (preferences, background, life details). Use this when you need to recall something specific about the user that may have been stored in a previous session.
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)

search_procedures — Search the procedures memory collection for stored interaction patterns (how the user likes to work, communicate, or learn).
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)

search_episodes — Search episodic memory for summaries of past conversations. Useful for recalling what was discussed or decided in previous sessions.
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)

search_audiobooks — Search AudioBookBay (audiobookbay.lu) for free audiobooks. Returns titles, authors, formats, total size, and magnet links ready to pass to add_torrent. Always present ALL results to the user with their sizes. If multiple results match or a book appears split into parts, ask the user which one(s) they want before calling add_torrent. Never auto-pick.
  query (string, required): Book title, author, or keywords

add_torrent — Send a magnet link to the system torrent client (Tixati) via xdg-open. Use this after finding an audiobook on AudioBookBay to start the download.
  magnet (string, required): Magnet link starting with "magnet:"

download_file — Download any file from a URL and save it to ~/Downloads. Use this for PDFs, EPUBs, or any binary file that fetch_url can't handle. Set ingest=true to automatically add the file to the knowledge base after downloading.
  url (string, required): Direct URL to the file
  filename (string, optional): Override the filename (auto-detected from URL if omitted)
  ingest (bool, optional): Ingest into knowledge base after download — supports PDF, EPUB, TXT, MD, RST (default false)

search_web — Search the web via SearXNG (aggregates Bing, DuckDuckGo, Brave, Google).
  query (string, required): Search query
  num_results (integer, optional): Number of results (default 8)

fetch_url — Fetch a URL and return its readable text content (HTML stripped).
  url (string, required): Full URL to fetch

screenshot_url — Take a screenshot of a web page (returns image for visual analysis).
  url (string, required): Full URL to screenshot
  full_page (bool, optional): Capture full scrollable page (default false)

ingest_file — Ingest a local document into the knowledge base (Qdrant sources). Supports PDF, EPUB, TXT, MD, RST.
  path (string, required): Path to the file (e.g. /mnt/WD/Books/book.pdf)
  title (string, optional): Override document title
  author (string, optional): Author name
  source_type (string, optional): book | document | paper | note (auto-detected from folder if omitted)

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

Media folders (use these for downloads):
  /mnt/WD/Books/       — ebooks (PDF, EPUB) — ingestible into knowledge base
  /mnt/WD/Audiobooks/  — audio books (MP3, M4B, etc.) — source: audiobookbay.lu
  /mnt/WD/Documents/   — documents, papers, notes — ingestible into knowledge base

After each tool call you will receive a <tool_result> block. Use it to inform your next step.
Do not emit multiple tool calls at once unless they are fully independent.
"""

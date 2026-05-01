TOOLS_SYSTEM_BLOCK = """
You have access to tools. Use them when they would help. Emit tool calls using this exact format:

<tool_call>
<function=tool_name>
<parameter=param_name>
value
</parameter>
</function>
</tool_call>

Call get_tool_description(tool_name) the first time you use a tool in a session, or when you're unsure about its parameters. On first use the spec is also returned automatically with the result.

Available tools:

get_tool_description — Get the full parameter spec for any tool before using it.

read_file — Read a file's contents.
write_file — Write content to a file.
edit_file — Replace exact text in a file.
delete_file — Delete a single file (refuses directories and protected paths).
get_file_info — Get metadata for a file or directory (size, permissions, timestamps).
move_file — Move or rename a file or directory.

bash — Run a shell command.
search_files — Search by filename pattern or content regex.
list_dir — List a directory's contents.

search_web — Search the web via SearXNG.
fetch_url — Fetch a URL and return its readable text content.
screenshot_url — Take a screenshot of a web page. Use http://localhost/#architecture for the canvas.
download_file — Download a file from a URL to ~/Downloads.

calculate — Evaluate a math expression.
convert_units — Convert between physical units.
convert_currency — Convert between currencies using live exchange rates.

calendar_today — Get today's date, day of week, Polish holiday status, and events.
calendar_get_events — Get events and holidays for a date or range.
calendar_add_event — Add a calendar event.
calendar_delete_event — Delete a calendar event by ID.

search_knowledge_base — Semantically search ingested books and documents.
list_knowledge_base — List all documents in the knowledge base.
ingest_file — Ingest a local document into the knowledge base.
delete_source — Delete a document from the knowledge base by exact title.

search_notes — Semantically search Obsidian vault notes.
list_notes — List all indexed notes.
ingest_note — Ingest or re-ingest a markdown file into the notes collection.
delete_note — Delete a note from the notes collection by exact title.

search_facts — Search stored facts about the user from memory.
search_procedures — Search stored interaction patterns from memory.
search_episodes — Search episodic memory for past conversation summaries.
save_memory — Save information directly to memory (facts/procedures/episodes).
update_memory — Replace an existing memory entry with updated text.
delete_memory — Delete an exact memory entry.

search_music — Search YouTube or SoundCloud for music (no download).
download_music — Download audio from a URL to /mnt/WD/Music. Always search first.
search_audiobooks — Search AudioBookBay for audiobooks (returns magnet links).
add_torrent — Send a magnet link to Tixati to start downloading.

navidrome_search — Search the local Navidrome music library.
navidrome_get_playlists — List all Navidrome playlists.
navidrome_get_playlist — Get tracks in a Navidrome playlist.
navidrome_create_playlist — Create a new Navidrome playlist.
navidrome_update_playlist — Add or remove tracks from a Navidrome playlist.
navidrome_delete_playlist — Delete a Navidrome playlist.
player_control — Control Feishin playback via MPRIS (play/pause/next/seek/volume).
player_now_playing — Get the currently playing track in Feishin.
player_load — Load Navidrome songs into the in-browser player.
soundcloud_get_playlists — List SoundCloud playlists from the logged-in account.
soundcloud_get_playlist — Get the full track list of a SoundCloud playlist.

canvas_draw — Draw shapes on the Architecture session canvas. Call get_tool_description('canvas_draw') first.
canvas_clear — Clear everything from the canvas.
canvas_get_state — Read all shapes on the canvas as text (type, position, label, color).
canvas_screenshot — Capture the canvas as an image to visually inspect what's drawn.

Media folders: /mnt/WD/Books/ | /mnt/WD/Audiobooks/ | /mnt/WD/Documents/ | /mnt/WD/Music/

After each tool call you will receive a <tool_result> block. Use it to inform your next step.
Do not emit multiple tool calls at once unless they are fully independent.
"""

TOOL_DETAILS = {
    "get_tool_description": """get_tool_description — Returns the full parameter spec for a tool.
  tool_name (string, required): Name of the tool to look up.""",

    "read_file": """read_file — Read a file's contents.
  path (string, required): Path to the file
  offset (integer, optional): Start line (default 0)
  limit (integer, optional): Max lines to read (default 200)""",

    "write_file": """write_file — Write content to a file (creates parent directories if needed). Requires approval.
  path (string, required): Destination path
  content (string, required): Content to write""",

    "edit_file": """edit_file — Replace exact text in a file. old_content must match exactly and uniquely. Requires approval.
  path (string, required): File to edit
  old_content (string, required): Exact text to replace
  new_content (string, required): Replacement text""",

    "delete_file": """delete_file — Delete a single file. Refuses directories, protected paths (.git, .env, .ssh), and workspace root. Requires approval.
  path (string, required): Path to the file to delete""",

    "get_file_info": """get_file_info — Get detailed metadata for a file or directory (size, permissions, owner, timestamps).
  path (string, required): Path to inspect""",

    "move_file": """move_file — Move or rename a file or directory. Requires approval.
  source (string, required): Current path
  destination (string, required): New path
  overwrite (bool, optional): Allow overwriting existing destination (default false)""",

    "bash": """bash — Run a shell command. Requires approval.
  command (string, required): Command to execute
  timeout (integer, optional): Timeout in seconds (default 30)""",

    "search_files": """search_files — Search by filename pattern or content regex.
  pattern (string, required): Glob pattern (name search) or regex (content search)
  path (string, optional): Directory to search (default: home)
  search_type (string, optional): "name" or "content" (default: "content")""",

    "list_dir": """list_dir — List a directory's contents.
  path (string, required): Directory path""",

    "search_web": """search_web — Search the web via SearXNG (aggregates Bing, DuckDuckGo, Brave, Google).
  query (string, required): Search query
  num_results (integer, optional): Number of results (default 8)""",

    "fetch_url": """fetch_url — Fetch a URL and return its readable text content (HTML stripped).
  url (string, required): Full URL to fetch""",

    "screenshot_url": """screenshot_url — Take a screenshot of a web page (returns image for visual analysis).
  url (string, required): Full URL. Use http://localhost/#architecture to see the canvas, http://localhost/#music for music session.
  full_page (bool, optional): Capture full scrollable page (default false)""",

    "download_file": """download_file — Download any file from a URL and save it to ~/Downloads.
  url (string, required): Direct URL to the file
  filename (string, optional): Override the filename (auto-detected from URL if omitted)
  ingest (bool, optional): Ingest into knowledge base after download — supports PDF, EPUB, TXT, MD, RST (default false)""",

    "calculate": """calculate — Evaluate a math expression.
  expression (string, required): e.g. "sqrt(2**8 + 144)" or "sin(pi/4)" — supports +,-,*,/,**,%, trig, log, sqrt, abs, round""",

    "convert_units": """convert_units — Convert between physical units (length, mass, temperature, speed, area, volume, energy, etc.).
  value (number, required): Numeric value to convert
  from_unit (string, required): Source unit, e.g. "km", "kg", "degC", "mph"
  to_unit (string, required): Target unit, e.g. "miles", "lb", "degF", "kph\"""",

    "convert_currency": """convert_currency — Convert between currencies using live exchange rates.
  amount (number, required): Amount to convert
  from_currency (string, required): ISO currency code, e.g. "USD", "PLN", "EUR"
  to_currency (string, required): ISO currency code""",

    "calendar_today": """calendar_today — Get today's date, day of week, Polish holiday status, and scheduled events. No parameters.""",

    "calendar_get_events": """calendar_get_events — Get events and Polish holidays for a date or date range.
  start_date (string, required): YYYY-MM-DD
  end_date (string, optional): YYYY-MM-DD (omit for single day)""",

    "calendar_add_event": """calendar_add_event — Add an event to the calendar. Requires approval.
  title (string, required): Event title
  date (string, required): YYYY-MM-DD
  time (string, optional): HH:MM — omit for all-day events
  description (string, optional): Extra details
  recurring (string, optional): none | daily | weekly | monthly | yearly (default: none)""",

    "calendar_delete_event": """calendar_delete_event — Delete a calendar event. Requires approval.
  event_id (integer, required): ID from calendar_get_events output""",

    "search_knowledge_base": """search_knowledge_base — Semantically search ingested books and documents (PDFs, EPUBs, papers). Use before searching the web for topics that may be in the library.
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)""",

    "list_knowledge_base": """list_knowledge_base — List all books and documents currently ingested in the knowledge base. No parameters.""",

    "ingest_file": """ingest_file — Ingest a local document into the knowledge base (Qdrant sources). Supports PDF, EPUB, TXT, MD, RST. Requires approval.
  path (string, required): Path to the file (e.g. /mnt/WD/Books/book.pdf)
  title (string, optional): Override document title
  author (string, optional): Author name
  source_type (string, optional): book | document | paper | note (auto-detected from folder if omitted)""",

    "delete_source": """delete_source — Delete a document and all its chunks from the knowledge base. Use list_knowledge_base first to confirm the exact title. Requires approval.
  title (string, required): Exact title of the document to delete""",

    "search_notes": """search_notes — Semantically search the Obsidian vault notes.
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)""",

    "list_notes": """list_notes — List all notes currently indexed in the notes collection. No parameters.""",

    "ingest_note": """ingest_note — Ingest or re-ingest a local markdown file into the notes collection. Use after editing a note so the updated content is searchable. Requires approval.
  path (string, required): Path to the markdown file
  title (string, optional): Override the note title""",

    "delete_note": """delete_note — Delete a note and all its chunks from the notes collection. Use list_notes first to confirm the exact title. Requires approval.
  title (string, required): Exact title of the note to delete""",

    "search_facts": """search_facts — Search the facts memory collection for stored facts about the user (preferences, background, life details).
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)""",

    "search_procedures": """search_procedures — Search the procedures memory collection for stored interaction patterns (how the user likes to work, communicate, or learn).
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)""",

    "search_episodes": """search_episodes — Search episodic memory for summaries of past conversations. Useful for recalling what was discussed or decided in previous sessions.
  query (string, required): What to search for
  top_k (integer, optional): Number of results (default 5)""",

    "save_memory": """save_memory — Save a piece of information directly to memory, bypassing the curator. Deduplication is automatic. Requires approval.
  text (string, required): The information to save
  collection (string, optional): facts (default) | procedures | episodes""",

    "update_memory": """update_memory — Replace an existing memory entry with corrected or updated text. Use search_facts/procedures/episodes first to get the exact stored text. Requires approval.
  old_text (string, required): Exact text of the existing entry to replace
  new_text (string, required): Updated text to store instead
  collection (string, optional): facts (default) | procedures | episodes""",

    "delete_memory": """delete_memory — Delete an exact memory entry. Use search_facts/procedures/episodes first to find the exact text. Requires approval.
  text (string, required): Exact text of the entry to delete
  collection (string, optional): facts (default) | procedures | episodes""",

    "search_music": """search_music — Search YouTube or SoundCloud for music without downloading. Call this first so the user can see results before approving a download.
  query (string, required): Song title, artist, or keywords
  source (string, optional): "youtube" or "soundcloud" (default: "youtube")
  limit (integer, optional): Number of results (default 5)""",

    "download_music": """download_music — Download audio from a YouTube or SoundCloud URL to /mnt/WD/Music in opus format. Requires approval. Always run search_music first and confirm URL with user.
  url (string, required): YouTube or SoundCloud URL (video, playlist, or channel)
  output_dir (string, optional): Destination folder (default: /mnt/WD/Music)
  audio_format (string, optional): "opus", "mp3", or "flac" (default: "opus")""",

    "search_audiobooks": """search_audiobooks — Search AudioBookBay (audiobookbay.lu) for free audiobooks. Returns titles, authors, formats, sizes, and magnet links. Always show ALL results and ask the user which one(s) to download before calling add_torrent.
  query (string, required): Book title, author, or keywords""",

    "add_torrent": """add_torrent — Send a magnet link to Tixati to start downloading. Use after search_audiobooks. Requires approval.
  magnet (string, required): Magnet link starting with "magnet:\"""",

    "navidrome_search": """navidrome_search — Search the local Navidrome music library for songs, albums, or artists.
  query (string, required): Search terms
  type (string, optional): "song", "album", or "artist" (default: "song")
  limit (integer, optional): Max results (default 10)""",

    "navidrome_get_playlists": """navidrome_get_playlists — List all playlists in Navidrome. No parameters.""",

    "navidrome_get_playlist": """navidrome_get_playlist — Get the tracks in a Navidrome playlist.
  playlist_id (string, required): Playlist ID from navidrome_get_playlists""",

    "navidrome_create_playlist": """navidrome_create_playlist — Create a new Navidrome playlist. Requires approval.
  name (string, required): Playlist name
  song_ids (list, optional): List of song IDs to add immediately""",

    "navidrome_update_playlist": """navidrome_update_playlist — Add or remove tracks from a Navidrome playlist. Use navidrome_get_playlist first to see current tracks. Requires approval.
  playlist_id (string, required): Playlist ID
  add_song_ids (list, optional): Song IDs to add
  remove_song_indices (list, optional): Zero-based track indices to remove
  name (string, optional): Rename the playlist""",

    "navidrome_delete_playlist": """navidrome_delete_playlist — Delete a Navidrome playlist. Requires approval.
  playlist_id (string, required): Playlist ID""",

    "player_control": """player_control — Control Feishin playback via MPRIS.
  action (string, required): play | pause | play_pause | next | previous | seek | volume
  value (float, optional): Seconds for seek, 0.0–1.0 for volume""",

    "player_now_playing": """player_now_playing — Get the currently playing track in Feishin with status and position. No parameters.""",

    "player_load": """player_load — Load Navidrome songs into the Accel in-browser player. Use navidrome_search first to get song IDs. Supports single tracks, albums, or full playlists. Player appears in the Music session widget.
  song_ids (list, required): List of Navidrome song IDs to queue and play""",

    "soundcloud_get_playlists": """soundcloud_get_playlists — List all SoundCloud playlists (public and private) from the logged-in account. No parameters.""",

    "soundcloud_get_playlist": """soundcloud_get_playlist — Get the full track list of a SoundCloud playlist.
  playlist_id (string, required): Playlist ID from soundcloud_get_playlists""",

    "canvas_draw": """canvas_draw — Draw shapes on the Architecture session canvas.

  shapes (list, required): A LIST of shape dicts, e.g. shapes=[{...}, {...}]
    Each shape dict has these fields:
      type (required): "geo" | "note" | "text" | "arrow"  — nothing else accepted
      text (str): label or content
      x, y (int): canvas position (default 100,100; use ~150px gaps between shapes)
      color: "blue"|"red"|"green"|"yellow"|"orange"|"violet"|"grey"|"black"|"white"|"light-blue"
      --- geo only ---
      geo (required for type=geo): "rectangle"|"ellipse"|"triangle"|"diamond"|"cloud"|"pentagon"|"hexagon"|"octagon"|"star"|"oval"|"trapezoid"|"heart"|"rhombus"|"x-box"|"check-box"
        NO "circle" — use geo="ellipse" with equal w and h for a circle.
      w, h (int): width and height in px (default 200×80; use equal values for circle-like ellipse)
      fill: "none"|"solid"|"semi"|"pattern"
      --- text/note only ---
      size: "s"|"m"|"l"|"xl"

Example call:
  shapes=[{"type":"geo","geo":"ellipse","w":150,"h":150,"x":200,"y":200,"color":"blue","fill":"solid"}]

Layout: left-to-right for sequences, top-to-bottom for hierarchies.""",

    "canvas_clear": """canvas_clear — Clear everything from the canvas. No parameters. Requires confirmation.""",

    "canvas_get_state": """canvas_get_state — Returns a text list of all shapes on the canvas (type, position, label, color, size). Use this to understand what's already drawn before adding more.""",

    "canvas_screenshot": """canvas_screenshot — Captures the current canvas as a PNG image and returns it for visual inspection. No parameters. Use after drawing to verify the result, or to read user-drawn content visually.""",
}


async def get_tool_description(tool_name: str = None, **kwargs) -> str:
    """Return the full parameter spec for a tool."""
    tool_name = tool_name or kwargs.get("name") or kwargs.get("tool") or kwargs.get("tool_name")
    if not tool_name:
        return "Provide a tool name, e.g. get_tool_description(tool_name='canvas_draw')"
    detail = TOOL_DETAILS.get(tool_name)
    if detail:
        return detail
    available = ", ".join(sorted(TOOL_DETAILS.keys()))
    return f"Unknown tool '{tool_name}'. Available: {available}"

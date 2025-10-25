"""
Claude Data Schema - Python Definitions
Language-agnostic schema implementation for Claude conversation data
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

# Type aliases
UUID = str
ISO8601 = str
UnixTimestamp = int

class MessageType(Enum):
    """Message type enumeration"""
    HUMAN = 'human'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'
    ERROR = 'error'
    TOOL = 'tool'
    TOOL_RESULT = 'tool_result'

# Claude Export Format (conversations.json, projects.json, users.json)
@dataclass
class ClaudeExportMessage:
    """Message in Claude export format"""
    uuid: UUID
    text: str
    sender: str  # 'human' or 'assistant'
    created_at: ISO8601
    updated_at: Optional[ISO8601] = None
    content: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    files: Optional[List[str]] = None

@dataclass
class ClaudeExportConversation:
    """Conversation in Claude export format"""
    uuid: UUID
    name: str
    created_at: ISO8601
    updated_at: ISO8601
    chat_messages: List[ClaudeExportMessage]
    summary: Optional[str] = None
    account: Optional[Dict[str, Any]] = None

@dataclass
class ClaudeExportDocument:
    """Document in Claude export format"""
    uuid: UUID
    filename: str
    content: str
    created_at: ISO8601

@dataclass
class ClaudeExportProject:
    """Project in Claude export format"""
    uuid: UUID
    name: str
    description: str
    created_at: ISO8601
    updated_at: ISO8601
    is_private: bool
    is_starter_project: bool
    creator: str
    docs: List[ClaudeExportDocument]
    prompt_template: Optional[str] = None

@dataclass
class ClaudeExportUser:
    """User in Claude export format"""
    uuid: UUID
    full_name: str
    email_address: str

# Claude Projects JSONL Format (.claude/projects/*)
@dataclass
class ToolCall:
    """Tool call information"""
    tool: str
    input: Dict[str, Any]
    id: str

@dataclass
class ToolResult:
    """Tool execution result"""
    tool: str
    output: Any
    id: str
    error: Optional[str] = None

@dataclass
class ClaudeProjectEntry:
    """Entry in Claude project JSONL format"""
    uuid: UUID
    sessionId: UUID
    type: str  # MessageType value
    message: str
    timestamp: UnixTimestamp
    parentUuid: Optional[UUID] = None
    cwd: Optional[str] = None
    gitBranch: Optional[str] = None
    isSidechain: Optional[bool] = None
    userType: Optional[str] = None  # 'free', 'pro', 'team'
    version: Optional[str] = None
    toolCalls: Optional[List[ToolCall]] = None
    toolResults: Optional[List[ToolResult]] = None
    errorDetails: Optional[Dict[str, Any]] = None

@dataclass
class Sidechain:
    """Sidechain conversation branch"""
    id: UUID
    parentUuid: UUID
    branchPoint: UUID
    messages: List[ClaudeProjectEntry]
    metadata: Optional[Dict[str, Any]] = None

# Search interfaces
@dataclass
class SearchQuery:
    """Search query parameters"""
    query: str
    strategy: str = 'intent'  # 'keyword', 'intent', 'semantic', 'hybrid'
    locations: Optional[List[str]] = None
    format: str = 'auto'  # 'auto', 'claude_export_json', 'claude_projects_jsonl'
    limit: int = 100
    offset: int = 0

@dataclass
class SearchResult:
    """Search result item"""
    uuid: UUID
    type: str  # 'conversation', 'project', 'message', 'document', 'user'
    title: str
    snippet: str
    score: float
    source: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    highlights: Optional[List[Dict[str, Any]]] = None

@dataclass
class DataLocation:
    """Data location configuration"""
    path: str
    format: str
    priority: int
    description: Optional[str] = None
    available: Optional[bool] = None

class ClaudeSearch:
    """Main search interface"""
    
    def __init__(self, locations: Optional[List[DataLocation]] = None):
        """Initialize search with data locations"""
        self.locations = locations or self._get_default_locations()
    
    def _get_default_locations(self) -> List[DataLocation]:
        """Get default search locations"""
        import os
        home = os.path.expanduser("~")
        return [
            DataLocation(
                path=f"{home}/nabia/search-archives",
                format="claude_export_json",
                priority=1,
                description="Primary search archive"
            ),
            DataLocation(
                path=f"{home}/.claude/projects",
                format="claude_projects_jsonl",
                priority=2,
                description="Claude Code projects"
            ),
            DataLocation(
                path=f"{home}/Downloads",
                format="claude_export_json",
                priority=3,
                description="Download location"
            ),
        ]
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Execute search across all locations"""
        raise NotImplementedError("Implement in subclass")
    
    def get_by_uuid(self, uuid: UUID, type: Optional[str] = None) -> Any:
        """Retrieve item by UUID"""
        raise NotImplementedError("Implement in subclass")
    
    def list_locations(self) -> List[DataLocation]:
        """List available data locations"""
        return self.locations

# Utility functions for cross-format conversion
def convert_export_to_jsonl(conversation: ClaudeExportConversation) -> List[ClaudeProjectEntry]:
    """Convert Claude export format to JSONL entries"""
    entries: list[ClaudeProjectEntry] = []
    session_id = conversation.uuid
    
    for msg in conversation.chat_messages:
        entry = ClaudeProjectEntry(
            uuid=msg.uuid,
            sessionId=session_id,
            type=msg.sender,
            message=msg.text,
            timestamp=int(datetime.fromisoformat(msg.created_at.replace('Z', '+00:00')).timestamp() * 1000),
            parentUuid=entries[-1].uuid if entries else None
        )
        entries.append(entry)
    
    return entries

def convert_jsonl_to_export(entries: List[ClaudeProjectEntry]) -> Optional[ClaudeExportConversation]:
    """Convert JSONL entries to Claude export format"""
    if not entries:
        return None

    messages: list[ClaudeExportMessage] = []
    for entry in entries:
        msg = ClaudeExportMessage(
            uuid=entry.uuid,
            text=entry.message,
            sender=entry.type if entry.type in ['human', 'assistant'] else 'assistant',
            created_at=datetime.fromtimestamp(entry.timestamp / 1000).isoformat() + 'Z'
        )
        messages.append(msg)
    
    return ClaudeExportConversation(
        uuid=entries[0].sessionId,
        name="Converted conversation",
        created_at=messages[0].created_at,
        updated_at=messages[-1].created_at,
        chat_messages=messages
    )

# Example usage
if __name__ == "__main__":
    # Create a search query
    query = SearchQuery(
        query="nabia federation",
        strategy="intent",
        limit=10
    )
    
    # Initialize search
    search = ClaudeSearch()
    
    # List available locations
    for loc in search.list_locations():
        print(f"Location: {loc.path} ({loc.format})")
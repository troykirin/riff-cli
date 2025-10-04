/**
 * Claude Data Schema - TypeScript Definitions
 * Language-agnostic schema implementation for Claude conversation data
 */

// Base types
export type UUID = string;
export type ISO8601 = string;
export type UnixTimestamp = number;

// Message types
export enum MessageType {
  Human = 'human',
  Assistant = 'assistant',
  System = 'system',
  Error = 'error',
  Tool = 'tool',
  ToolResult = 'tool_result'
}

// Claude Export Format (conversations.json, projects.json, users.json)
export namespace ClaudeExport {
  export interface Conversation {
    uuid: UUID;
    name: string;
    created_at: ISO8601;
    updated_at: ISO8601;
    summary?: string;
    account?: Record<string, any>;
    chat_messages: Message[];
  }

  export interface Message {
    uuid: UUID;
    text: string;
    content?: ContentBlock[];
    sender: 'human' | 'assistant';
    created_at: ISO8601;
    updated_at?: ISO8601;
    attachments?: Attachment[];
    files?: string[];
  }

  export interface ContentBlock {
    type: 'text' | 'code' | 'tool_use' | 'tool_result';
    text?: string;
    language?: string;
    tool_name?: string;
    tool_input?: Record<string, any>;
    tool_output?: any;
  }

  export interface Attachment {
    filename: string;
    content_type: string;
    size: number;
  }

  export interface Project {
    uuid: UUID;
    name: string;
    description: string;
    created_at: ISO8601;
    updated_at: ISO8601;
    is_private: boolean;
    is_starter_project: boolean;
    prompt_template?: string;
    creator: string;
    docs: Document[];
  }

  export interface Document {
    uuid: UUID;
    filename: string;
    content: string;
    created_at: ISO8601;
  }

  export interface User {
    uuid: UUID;
    full_name: string;
    email_address: string;
  }
}

// Claude Projects JSONL Format (.claude/projects/*)
export namespace ClaudeProjects {
  export interface Entry {
    uuid: UUID;
    sessionId: UUID;
    parentUuid?: UUID;  // For message threading
    type: MessageType | string;
    message: string;
    timestamp: UnixTimestamp;
    cwd?: string;  // Current working directory
    gitBranch?: string;
    isSidechain?: boolean;  // Sidechain messages
    userType?: 'free' | 'pro' | 'team';
    version?: string;
    
    // Tool-specific fields
    toolCalls?: ToolCall[];
    toolResults?: ToolResult[];
    errorDetails?: ErrorDetails;
  }

  export interface ToolCall {
    tool: string;
    input: Record<string, any>;
    id: string;
  }

  export interface ToolResult {
    tool: string;
    output: any;
    id: string;
    error?: string;
  }

  export interface ErrorDetails {
    code: string;
    message: string;
    stack?: string;
  }

  // Sidechain represents alternative conversation branches
  export interface Sidechain {
    id: UUID;
    parentUuid: UUID;
    branchPoint: UUID;
    messages: Entry[];
    metadata?: {
      reason?: string;
      created_at?: UnixTimestamp;
      is_active?: boolean;
    };
  }
}

// Search interfaces
export interface SearchQuery {
  query: string;
  strategy?: 'keyword' | 'intent' | 'semantic' | 'hybrid';
  locations?: string[];
  format?: 'auto' | 'claude_export_json' | 'claude_projects_jsonl';
  limit?: number;
  offset?: number;
}

export interface SearchResult {
  uuid: UUID;
  type: 'conversation' | 'project' | 'message' | 'document' | 'user';
  title: string;
  snippet: string;
  score: number;
  source: {
    path: string;
    format: string;
    line?: number;  // For JSONL
  };
  metadata?: Record<string, any>;
  highlights?: Array<{
    field: string;
    fragments: string[];
  }>;
}

// Search strategy configurations
export interface SearchStrategy {
  name: string;
  description: string;
  enhanceKeywords?: boolean;
  recursiveDepth?: number;
  boostFields?: string[];
  weightConfig?: Record<string, number>;
}

// Data location configuration
export interface DataLocation {
  path: string;
  format: 'claude_export_json' | 'claude_projects_jsonl';
  priority: number;
  description?: string;
  available?: boolean;
}

// Main search interface
export interface ClaudeSearch {
  // Configuration
  locations: DataLocation[];
  defaultStrategy: SearchStrategy;
  
  // Methods
  search(query: SearchQuery): Promise<SearchResult[]>;
  getByUuid(uuid: UUID, type?: string): Promise<any>;
  listLocations(): DataLocation[];
  
  // Index operations
  buildIndex?(locations?: string[]): Promise<void>;
  clearIndex?(): void;
}

// Utility types for language-agnostic framework
export type SchemaField = {
  type: 'string' | 'number' | 'boolean' | 'object' | 'array' | 'timestamp';
  format?: string;
  searchable?: boolean;
  weight?: number;
  description?: string;
};

export type Schema = {
  [key: string]: SchemaField | Schema;
};

// Export unified interface
export interface UnifiedClaudeData {
  conversations?: ClaudeExport.Conversation[];
  projects?: ClaudeExport.Project[];
  users?: ClaudeExport.User[];
  sessions?: ClaudeProjects.Entry[];
  sidechains?: ClaudeProjects.Sidechain[];
}
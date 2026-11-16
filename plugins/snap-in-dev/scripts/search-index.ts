#!/usr/bin/env ts-node
/**
 * Search Utility for Snap-in Index
 *
 * A comprehensive search tool for finding relevant snap-in examples
 * based on various criteria like type, features, complexity, keywords, etc.
 *
 * Usage:
 *   npx ts-node scripts/search-index.ts --type=event-driven --features=keyrings
 *   npx ts-node scripts/search-index.ts --keyword=slack --complexity=beginner
 *   npx ts-node scripts/search-index.ts --use-case=addSlashCommands
 */

import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// Types
// ============================================================================

export interface ExampleEntry {
  id: string;
  name: string;
  path: string;
  description: string;
  type: string[];
  hasManifest: boolean;
  features: string[];
  eventSources?: string[];
  eventTypes?: string[];
  commands?: string[];
  operations?: string[];
  hookTypes?: string[];
  cronExpression?: string;
  complexity: 'beginner' | 'intermediate' | 'advanced';
  dependencies?: string[];
  keyFiles: string[];
  learnAbout: string[];
}

export interface IndexJson {
  repository: {
    name: string;
    description: string;
    totalExamples: number;
    deployableSnapIns: number;
    templates: number;
    language: string;
    runtime: string;
    primarySDK: string;
    generatedAt: string;
  };
  snapInTypes: Record<string, { description: string; examples: string[] }>;
  examples: ExampleEntry[];
  manifestPatterns: {
    eventSources: Record<string, any>;
    inputTypes: Record<string, any>;
    keyrings: any;
  };
  codePatterns: Record<string, any>;
  useCaseIndex: Record<string, string[]>;
  complexity: Record<string, string[]>;
}

export interface SearchCriteria {
  /** Snap-in type: event-driven, command-based, timer-based, etc. */
  type?: string;
  /** Required features: keyrings, automation, snap-kit-actions, etc. */
  features?: string[];
  /** Any of these features (OR logic) */
  anyFeatures?: string[];
  /** Event type: work_created, work_updated, etc. */
  eventType?: string;
  /** Complexity level: beginner, intermediate, advanced */
  complexity?: 'beginner' | 'intermediate' | 'advanced';
  /** Keyword to search in name, description, and id */
  keyword?: string;
  /** Use case from useCaseIndex */
  useCase?: string;
  /** Learn about topic */
  learnAbout?: string;
  /** Has specific command pattern */
  commandPattern?: string;
  /** Has specific operation */
  operation?: string;
  /** Maximum number of results */
  limit?: number;
}

export interface SearchResult {
  example: ExampleEntry;
  relevanceScore: number;
  matchedCriteria: string[];
}

export interface ExplorationContext {
  snapIn: ExampleEntry;
  absolutePath: string;
  filesToRead: Array<{
    path: string;
    absolutePath: string;
    purpose: string;
  }>;
  summary: string;
}

// ============================================================================
// Index Loader
// ============================================================================

export class SnapInIndex {
  private index: IndexJson;
  private indexPath: string;
  private rootDir: string;

  constructor(indexPath: string) {
    this.indexPath = indexPath;
    this.rootDir = path.dirname(indexPath);

    if (!fs.existsSync(indexPath)) {
      throw new Error(`Index file not found: ${indexPath}`);
    }

    this.index = JSON.parse(fs.readFileSync(indexPath, 'utf-8'));
  }

  // ==========================================================================
  // Basic Accessors
  // ==========================================================================

  getRepository() {
    return this.index.repository;
  }

  getAllExamples(): ExampleEntry[] {
    return this.index.examples;
  }

  getSnapInTypes(): Record<string, { description: string; examples: string[] }> {
    return this.index.snapInTypes;
  }

  getUseCaseIndex(): Record<string, string[]> {
    return this.index.useCaseIndex;
  }

  getComplexityIndex(): Record<string, string[]> {
    return this.index.complexity;
  }

  getManifestPatterns() {
    return this.index.manifestPatterns;
  }

  getCodePatterns() {
    return this.index.codePatterns;
  }

  // ==========================================================================
  // Search Methods
  // ==========================================================================

  /**
   * Search by snap-in type (event-driven, command-based, etc.)
   */
  searchByType(type: string): ExampleEntry[] {
    return this.index.examples.filter(e => e.type.includes(type));
  }

  /**
   * Search by use case from useCaseIndex
   */
  searchByUseCase(useCase: string): ExampleEntry[] {
    const paths = this.index.useCaseIndex[useCase] || [];
    return this.index.examples.filter(e => paths.includes(e.path));
  }

  /**
   * Search by complexity level
   */
  searchByComplexity(complexity: 'beginner' | 'intermediate' | 'advanced'): ExampleEntry[] {
    const paths = this.index.complexity[complexity] || [];
    return this.index.examples.filter(e => paths.includes(e.path));
  }

  /**
   * Search by features (all must match)
   */
  searchByFeatures(features: string[]): ExampleEntry[] {
    return this.index.examples.filter(e =>
      features.every(f => e.features.includes(f))
    );
  }

  /**
   * Search by any features (at least one must match)
   */
  searchByAnyFeatures(features: string[]): ExampleEntry[] {
    return this.index.examples.filter(e =>
      features.some(f => e.features.includes(f))
    );
  }

  /**
   * Search by event type
   */
  searchByEventType(eventType: string): ExampleEntry[] {
    return this.index.examples.filter(e =>
      e.eventTypes?.includes(eventType)
    );
  }

  /**
   * Search by keyword in name, description, id, and learnAbout
   */
  searchByKeyword(keyword: string): ExampleEntry[] {
    const kw = keyword.toLowerCase();
    return this.index.examples.filter(e =>
      e.name.toLowerCase().includes(kw) ||
      e.description.toLowerCase().includes(kw) ||
      e.id.toLowerCase().includes(kw) ||
      e.learnAbout.some(t => t.toLowerCase().includes(kw)) ||
      e.features.some(f => f.toLowerCase().includes(kw))
    );
  }

  /**
   * Search by learnAbout topic
   */
  searchByLearnAbout(topic: string): ExampleEntry[] {
    const t = topic.toLowerCase();
    return this.index.examples.filter(e =>
      e.learnAbout.some(l => l.toLowerCase().includes(t))
    );
  }

  /**
   * Search by command pattern
   */
  searchByCommand(pattern: string): ExampleEntry[] {
    const p = pattern.toLowerCase();
    return this.index.examples.filter(e =>
      e.commands?.some(c => c.toLowerCase().includes(p))
    );
  }

  /**
   * Search by operation name
   */
  searchByOperation(operation: string): ExampleEntry[] {
    const op = operation.toLowerCase();
    return this.index.examples.filter(e =>
      e.operations?.some(o => o.toLowerCase().includes(op))
    );
  }

  /**
   * Advanced multi-criteria search with relevance scoring
   */
  search(criteria: SearchCriteria): SearchResult[] {
    let results: SearchResult[] = this.index.examples.map(example => ({
      example,
      relevanceScore: 0,
      matchedCriteria: [] as string[]
    }));

    // Filter and score by type
    if (criteria.type) {
      results = results.filter(r => r.example.type.includes(criteria.type!));
      results.forEach(r => {
        r.relevanceScore += 10;
        r.matchedCriteria.push(`type:${criteria.type}`);
      });
    }

    // Filter and score by features (all must match)
    if (criteria.features?.length) {
      results = results.filter(r =>
        criteria.features!.every(f => r.example.features.includes(f))
      );
      results.forEach(r => {
        r.relevanceScore += criteria.features!.length * 5;
        r.matchedCriteria.push(`features:[${criteria.features!.join(',')}]`);
      });
    }

    // Score by any features (at least one must match)
    if (criteria.anyFeatures?.length) {
      results = results.filter(r =>
        criteria.anyFeatures!.some(f => r.example.features.includes(f))
      );
      results.forEach(r => {
        const matchCount = criteria.anyFeatures!.filter(f =>
          r.example.features.includes(f)
        ).length;
        r.relevanceScore += matchCount * 3;
        r.matchedCriteria.push(`anyFeatures:${matchCount}/${criteria.anyFeatures!.length}`);
      });
    }

    // Filter and score by event type
    if (criteria.eventType) {
      results = results.filter(r =>
        r.example.eventTypes?.includes(criteria.eventType!)
      );
      results.forEach(r => {
        r.relevanceScore += 8;
        r.matchedCriteria.push(`eventType:${criteria.eventType}`);
      });
    }

    // Filter and score by complexity
    if (criteria.complexity) {
      results = results.filter(r => r.example.complexity === criteria.complexity);
      results.forEach(r => {
        r.relevanceScore += 5;
        r.matchedCriteria.push(`complexity:${criteria.complexity}`);
      });
    }

    // Filter and score by use case
    if (criteria.useCase) {
      const paths = this.index.useCaseIndex[criteria.useCase] || [];
      results = results.filter(r => paths.includes(r.example.path));
      results.forEach(r => {
        r.relevanceScore += 10;
        r.matchedCriteria.push(`useCase:${criteria.useCase}`);
      });
    }

    // Score by keyword (doesn't filter, just boosts score)
    if (criteria.keyword) {
      const kw = criteria.keyword.toLowerCase();
      results.forEach(r => {
        let keywordScore = 0;
        if (r.example.name.toLowerCase().includes(kw)) keywordScore += 10;
        if (r.example.id.toLowerCase().includes(kw)) keywordScore += 8;
        if (r.example.description.toLowerCase().includes(kw)) keywordScore += 5;
        if (r.example.learnAbout.some(t => t.toLowerCase().includes(kw))) keywordScore += 3;
        if (r.example.features.some(f => f.toLowerCase().includes(kw))) keywordScore += 3;

        if (keywordScore > 0) {
          r.relevanceScore += keywordScore;
          r.matchedCriteria.push(`keyword:${criteria.keyword}`);
        }
      });

      // Only keep results that matched the keyword
      results = results.filter(r =>
        r.matchedCriteria.some(c => c.startsWith('keyword:'))
      );
    }

    // Filter by learnAbout
    if (criteria.learnAbout) {
      const topic = criteria.learnAbout.toLowerCase();
      results = results.filter(r =>
        r.example.learnAbout.some(l => l.toLowerCase().includes(topic))
      );
      results.forEach(r => {
        r.relevanceScore += 5;
        r.matchedCriteria.push(`learnAbout:${criteria.learnAbout}`);
      });
    }

    // Filter by command pattern
    if (criteria.commandPattern) {
      const pattern = criteria.commandPattern.toLowerCase();
      results = results.filter(r =>
        r.example.commands?.some(c => c.toLowerCase().includes(pattern))
      );
      results.forEach(r => {
        r.relevanceScore += 8;
        r.matchedCriteria.push(`command:${criteria.commandPattern}`);
      });
    }

    // Filter by operation
    if (criteria.operation) {
      const op = criteria.operation.toLowerCase();
      results = results.filter(r =>
        r.example.operations?.some(o => o.toLowerCase().includes(op))
      );
      results.forEach(r => {
        r.relevanceScore += 8;
        r.matchedCriteria.push(`operation:${criteria.operation}`);
      });
    }

    // Sort by relevance score (highest first)
    results.sort((a, b) => b.relevanceScore - a.relevanceScore);

    // Apply limit
    if (criteria.limit && criteria.limit > 0) {
      results = results.slice(0, criteria.limit);
    }

    return results;
  }

  // ==========================================================================
  // Exploration Helpers
  // ==========================================================================

  /**
   * Generate exploration context for a snap-in
   */
  getExplorationContext(exampleId: string): ExplorationContext | null {
    const example = this.index.examples.find(e => e.id === exampleId || e.path === exampleId);
    if (!example) return null;

    const absolutePath = path.join(this.rootDir, example.path);

    const filesToRead = example.keyFiles.map(file => {
      const purpose = this.inferFilePurpose(file);
      return {
        path: file,
        absolutePath: path.join(absolutePath, file),
        purpose
      };
    });

    const summary = this.generateSummary(example);

    return {
      snapIn: example,
      absolutePath,
      filesToRead,
      summary
    };
  }

  /**
   * Get multiple exploration contexts
   */
  getExplorationContexts(exampleIds: string[]): ExplorationContext[] {
    return exampleIds
      .map(id => this.getExplorationContext(id))
      .filter((ctx): ctx is ExplorationContext => ctx !== null);
  }

  /**
   * Infer the purpose of a file based on its path
   */
  private inferFilePurpose(filePath: string): string {
    const fileName = path.basename(filePath);
    const dirName = path.basename(path.dirname(filePath));

    if (fileName === 'manifest.yaml') {
      return 'Snap-in configuration: functions, event sources, inputs, keyrings, automations';
    }
    if (fileName === 'function-factory.ts') {
      return 'Function registry mapping names to implementations';
    }
    if (fileName === 'main.ts' && filePath.includes('src/')) {
      return 'Local testing entry point';
    }
    if (fileName === 'test-runner.ts') {
      return 'Test execution infrastructure';
    }
    if (fileName === 'index.ts' && filePath.includes('functions/')) {
      return `Function implementation for ${dirName}`;
    }
    if (dirName === 'common' || dirName === 'commons') {
      return `Shared utility: ${fileName.replace('.ts', '')}`;
    }
    if (fileName.includes('utils') || fileName.includes('helper')) {
      return 'Utility functions and helpers';
    }
    if (fileName.includes('types')) {
      return 'TypeScript type definitions';
    }
    if (fileName.includes('constants')) {
      return 'Constant values and configuration';
    }
    if (filePath.includes('operation_handler')) {
      return `Operation implementation: ${fileName.replace('.ts', '')}`;
    }

    return 'Implementation file';
  }

  /**
   * Generate a summary of what can be learned from this snap-in
   */
  private generateSummary(example: ExampleEntry): string {
    const parts: string[] = [];

    parts.push(`**${example.name}** (${example.complexity})`);
    parts.push(`${example.description}`);
    parts.push('');

    if (example.type.length > 0) {
      parts.push(`**Type:** ${example.type.join(', ')}`);
    }

    if (example.features.length > 0) {
      parts.push(`**Features:** ${example.features.join(', ')}`);
    }

    if (example.eventSources?.length) {
      parts.push(`**Event Sources:** ${example.eventSources.join(', ')}`);
    }

    if (example.eventTypes?.length) {
      parts.push(`**Event Types:** ${example.eventTypes.join(', ')}`);
    }

    if (example.commands?.length) {
      parts.push(`**Commands:** ${example.commands.join(', ')}`);
    }

    if (example.operations?.length) {
      parts.push(`**Operations:** ${example.operations.join(', ')}`);
    }

    if (example.learnAbout.length > 0) {
      parts.push(`**Learn About:** ${example.learnAbout.join(', ')}`);
    }

    return parts.join('\n');
  }

  // ==========================================================================
  // Statistics and Discovery
  // ==========================================================================

  /**
   * Get all unique features across all snap-ins
   */
  getAllFeatures(): string[] {
    const features = new Set<string>();
    this.index.examples.forEach(e => e.features.forEach(f => features.add(f)));
    return Array.from(features).sort();
  }

  /**
   * Get all unique event types
   */
  getAllEventTypes(): string[] {
    const types = new Set<string>();
    this.index.examples.forEach(e => e.eventTypes?.forEach(t => types.add(t)));
    return Array.from(types).sort();
  }

  /**
   * Get all available use cases
   */
  getAllUseCases(): string[] {
    return Object.keys(this.index.useCaseIndex).sort();
  }

  /**
   * Get all snap-in types
   */
  getAllSnapInTypes(): string[] {
    return Object.keys(this.index.snapInTypes).sort();
  }

  /**
   * Get feature usage statistics
   */
  getFeatureStats(): Record<string, number> {
    const stats: Record<string, number> = {};
    this.index.examples.forEach(e => {
      e.features.forEach(f => {
        stats[f] = (stats[f] || 0) + 1;
      });
    });
    return stats;
  }

  /**
   * Find similar snap-ins based on feature overlap
   */
  findSimilar(exampleId: string, limit = 5): ExampleEntry[] {
    const target = this.index.examples.find(e => e.id === exampleId || e.path === exampleId);
    if (!target) return [];

    const scored = this.index.examples
      .filter(e => e.id !== target.id)
      .map(e => {
        const commonFeatures = e.features.filter(f => target.features.includes(f));
        const commonTypes = e.type.filter(t => target.type.includes(t));
        const score = commonFeatures.length * 2 + commonTypes.length * 3;
        return { example: e, score };
      })
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);

    return scored.map(s => s.example);
  }
}

// ============================================================================
// Exploration Workflow
// ============================================================================

export interface ExplorationStep {
  step: number;
  action: string;
  details: string;
  files?: string[];
}

export class ExplorationWorkflow {
  private index: SnapInIndex;

  constructor(index: SnapInIndex) {
    this.index = index;
  }

  /**
   * Generate a complete exploration workflow for a search query
   */
  generateWorkflow(criteria: SearchCriteria): {
    searchResults: SearchResult[];
    explorationSteps: ExplorationStep[];
    contextForPrompt: string;
  } {
    // Step 1: Search
    const searchResults = this.index.search(criteria);

    // Step 2: Generate exploration steps
    const explorationSteps = this.generateSteps(searchResults);

    // Step 3: Generate context for prompt
    const contextForPrompt = this.generatePromptContext(searchResults.slice(0, 5));

    return {
      searchResults,
      explorationSteps,
      contextForPrompt
    };
  }

  /**
   * Generate step-by-step exploration instructions
   */
  private generateSteps(results: SearchResult[]): ExplorationStep[] {
    const steps: ExplorationStep[] = [];
    let stepNum = 1;

    // Overview step
    steps.push({
      step: stepNum++,
      action: 'Review Search Results',
      details: `Found ${results.length} matching snap-ins. Top matches by relevance score.`
    });

    // For top 3 results, generate detailed exploration steps
    const topResults = results.slice(0, 3);

    for (const result of topResults) {
      const ctx = this.index.getExplorationContext(result.example.id);
      if (!ctx) continue;

      // Manifest step
      const manifestFile = ctx.filesToRead.find(f => f.path === 'manifest.yaml');
      if (manifestFile) {
        steps.push({
          step: stepNum++,
          action: `Analyze manifest.yaml for ${result.example.name}`,
          details: 'Understand configuration: functions, event sources, inputs, keyrings, automations',
          files: [manifestFile.absolutePath]
        });
      }

      // Function files step
      const functionFiles = ctx.filesToRead.filter(f =>
        f.path.includes('functions/') && f.path.endsWith('index.ts')
      );
      if (functionFiles.length > 0) {
        steps.push({
          step: stepNum++,
          action: `Study function implementations in ${result.example.name}`,
          details: `Analyze ${functionFiles.length} function(s) to understand implementation patterns`,
          files: functionFiles.map(f => f.absolutePath)
        });
      }

      // Utility files step
      const utilFiles = ctx.filesToRead.filter(f =>
        f.path.includes('common/') || f.path.includes('utils')
      );
      if (utilFiles.length > 0) {
        steps.push({
          step: stepNum++,
          action: `Review shared utilities in ${result.example.name}`,
          details: 'Understand reusable patterns and helper functions',
          files: utilFiles.map(f => f.absolutePath)
        });
      }
    }

    // Summary step
    steps.push({
      step: stepNum++,
      action: 'Synthesize Findings',
      details: 'Combine learnings from analyzed examples to inform implementation approach'
    });

    return steps;
  }

  /**
   * Generate formatted context for including in prompts
   */
  private generatePromptContext(results: SearchResult[]): string {
    const sections: string[] = [];

    sections.push('## Relevant Snap-in Examples\n');

    for (const result of results) {
      const ctx = this.index.getExplorationContext(result.example.id);
      if (!ctx) continue;

      sections.push(`### ${ctx.snapIn.name}`);
      sections.push(`**Path:** \`${ctx.absolutePath}\``);
      sections.push(`**Relevance:** Score ${result.relevanceScore} (${result.matchedCriteria.join(', ')})`);
      sections.push(`**Description:** ${ctx.snapIn.description}`);
      sections.push('');

      sections.push('**Key Files:**');
      for (const file of ctx.filesToRead.slice(0, 5)) {
        sections.push(`- \`${file.absolutePath}\` - ${file.purpose}`);
      }
      sections.push('');

      if (ctx.snapIn.learnAbout.length > 0) {
        sections.push(`**Learn About:** ${ctx.snapIn.learnAbout.join(', ')}`);
      }

      sections.push('---\n');
    }

    return sections.join('\n');
  }

  /**
   * Generate a concise summary for context enrichment
   */
  generateConciseSummary(results: SearchResult[], maxExamples = 3): string {
    const lines: string[] = [];

    lines.push(`Found ${results.length} relevant examples.`);
    lines.push('');

    for (const result of results.slice(0, maxExamples)) {
      const e = result.example;
      lines.push(`**${e.name}** (\`${e.path}\`)`);
      lines.push(`  Type: ${e.type.join(', ')} | Complexity: ${e.complexity}`);
      lines.push(`  Features: ${e.features.slice(0, 5).join(', ')}${e.features.length > 5 ? '...' : ''}`);
      lines.push(`  Key patterns: ${e.learnAbout.join(', ')}`);
      lines.push('');
    }

    return lines.join('\n');
  }
}

// ============================================================================
// CLI Interface
// ============================================================================

function parseArgs(): SearchCriteria & { indexPath?: string; showStats?: boolean; showHelp?: boolean } {
  const args = process.argv.slice(2);
  const result: SearchCriteria & { indexPath?: string; showStats?: boolean; showHelp?: boolean } = {};

  for (const arg of args) {
    if (arg === '--help' || arg === '-h') {
      result.showHelp = true;
      continue;
    }
    if (arg === '--stats') {
      result.showStats = true;
      continue;
    }

    const match = arg.match(/^--(\w+)=(.+)$/);
    if (match) {
      const [, key, value] = match;
      switch (key) {
        case 'type':
          result.type = value;
          break;
        case 'features':
          result.features = value.split(',');
          break;
        case 'anyFeatures':
          result.anyFeatures = value.split(',');
          break;
        case 'eventType':
          result.eventType = value;
          break;
        case 'complexity':
          result.complexity = value as 'beginner' | 'intermediate' | 'advanced';
          break;
        case 'keyword':
          result.keyword = value;
          break;
        case 'useCase':
          result.useCase = value;
          break;
        case 'learnAbout':
          result.learnAbout = value;
          break;
        case 'command':
          result.commandPattern = value;
          break;
        case 'operation':
          result.operation = value;
          break;
        case 'limit':
          result.limit = parseInt(value, 10);
          break;
        case 'index':
          result.indexPath = value;
          break;
      }
    }
  }

  return result;
}

function printHelp() {
  console.log(`
Snap-in Index Search Utility

USAGE:
  npx ts-node scripts/search-index.ts [OPTIONS]

OPTIONS:
  --type=<type>           Filter by snap-in type (event-driven, command-based, timer-based,
                          external-webhook, operations, hook-based, interactive-ui)
  --features=<f1,f2>      Filter by features (all must match)
  --anyFeatures=<f1,f2>   Filter by features (any must match)
  --eventType=<type>      Filter by event type (work_created, work_updated, etc.)
  --complexity=<level>    Filter by complexity (beginner, intermediate, advanced)
  --keyword=<word>        Search in name, description, id, learnAbout, features
  --useCase=<case>        Filter by use case (addSlashCommands, createInteractiveUI, etc.)
  --learnAbout=<topic>    Filter by learning topic
  --command=<pattern>     Filter by command name pattern
  --operation=<name>      Filter by operation name
  --limit=<n>             Limit number of results
  --index=<path>          Path to index.json (default: ../index.json)
  --stats                 Show index statistics
  --help, -h              Show this help message

EXAMPLES:
  # Find event-driven snap-ins with keyrings
  npx ts-node scripts/search-index.ts --type=event-driven --features=keyrings

  # Find beginner-friendly command-based snap-ins
  npx ts-node scripts/search-index.ts --type=command-based --complexity=beginner

  # Search for Slack-related snap-ins
  npx ts-node scripts/search-index.ts --keyword=slack --limit=10

  # Find snap-ins that handle work_created events
  npx ts-node scripts/search-index.ts --eventType=work_created

  # Find snap-ins with operations
  npx ts-node scripts/search-index.ts --type=operations --limit=5

  # Show index statistics
  npx ts-node scripts/search-index.ts --stats
`);
}

function printStats(index: SnapInIndex) {
  const repo = index.getRepository();
  console.log('\n=== Index Statistics ===\n');
  console.log(`Total Examples: ${repo.totalExamples}`);
  console.log(`Deployable: ${repo.deployableSnapIns}`);
  console.log(`Templates: ${repo.templates}`);
  console.log(`Generated: ${repo.generatedAt}`);

  console.log('\n--- Snap-in Types ---');
  const types = index.getSnapInTypes();
  Object.entries(types).forEach(([type, data]) => {
    console.log(`  ${type}: ${data.examples.length} examples`);
  });

  console.log('\n--- Complexity Distribution ---');
  const complexity = index.getComplexityIndex();
  Object.entries(complexity).forEach(([level, examples]) => {
    console.log(`  ${level}: ${examples.length} examples`);
  });

  console.log('\n--- Top Features ---');
  const featureStats = index.getFeatureStats();
  const topFeatures = Object.entries(featureStats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);
  topFeatures.forEach(([feature, count]) => {
    console.log(`  ${feature}: ${count}`);
  });

  console.log('\n--- Available Use Cases ---');
  index.getAllUseCases().forEach(uc => console.log(`  ${uc}`));
}

function main() {
  const args = parseArgs();

  if (args.showHelp) {
    printHelp();
    return;
  }

  const indexPath = args.indexPath || path.resolve(__dirname, '..', 'index.json');
  const index = new SnapInIndex(indexPath);

  if (args.showStats) {
    printStats(index);
    return;
  }

  // Check if any search criteria provided
  const hasCriteria = args.type || args.features || args.anyFeatures ||
    args.eventType || args.complexity || args.keyword ||
    args.useCase || args.learnAbout || args.commandPattern || args.operation;

  if (!hasCriteria) {
    console.log('No search criteria provided. Use --help for usage information.');
    console.log('\nQuick examples:');
    console.log('  --type=event-driven');
    console.log('  --keyword=slack');
    console.log('  --complexity=beginner');
    console.log('  --stats');
    return;
  }

  // Perform search
  const criteria: SearchCriteria = {
    type: args.type,
    features: args.features,
    anyFeatures: args.anyFeatures,
    eventType: args.eventType,
    complexity: args.complexity,
    keyword: args.keyword,
    useCase: args.useCase,
    learnAbout: args.learnAbout,
    commandPattern: args.commandPattern,
    operation: args.operation,
    limit: args.limit || 10
  };

  const workflow = new ExplorationWorkflow(index);
  const { searchResults, explorationSteps, contextForPrompt } = workflow.generateWorkflow(criteria);

  console.log(`\n=== Search Results (${searchResults.length} found) ===\n`);

  for (const result of searchResults.slice(0, criteria.limit || 10)) {
    const e = result.example;
    console.log(`[${result.relevanceScore}] ${e.name} (${e.path})`);
    console.log(`    Type: ${e.type.join(', ')} | Complexity: ${e.complexity}`);
    console.log(`    ${e.description.slice(0, 100)}${e.description.length > 100 ? '...' : ''}`);
    console.log(`    Matched: ${result.matchedCriteria.join(', ')}`);
    console.log('');
  }

  console.log('\n=== Exploration Steps ===\n');
  for (const step of explorationSteps) {
    console.log(`${step.step}. ${step.action}`);
    console.log(`   ${step.details}`);
    if (step.files) {
      step.files.slice(0, 3).forEach(f => console.log(`   - ${f}`));
    }
    console.log('');
  }
}

// Run if executed directly
if (require.main === module) {
  main();
}

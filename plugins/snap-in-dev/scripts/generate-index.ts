#!/usr/bin/env ts-node
/**
 * Script to programmatically generate index.json for snap-in examples
 *
 * Usage: npx ts-node scripts/generate-index.ts
 *
 * This script analyzes the repository structure, manifest.yaml files,
 * package.json dependencies, and code patterns to generate a comprehensive
 * index of all snap-in examples.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';

// Types
interface ManifestEventSource {
  name: string;
  type: string;
  config?: {
    event_types?: string[];
    cron?: string;
    policy?: string;
  };
  filter?: { jq_query?: string };
}

interface ManifestCommand {
  name: string;
  namespace?: string;
  description?: string;
  function?: string;
}

interface ManifestOperation {
  name: string;
  slug?: string;
  function?: string;
  inputs?: any;
  outputs?: any;
}

interface ManifestHook {
  type: string;
  function: string;
}

interface ManifestInput {
  name: string;
  field_type: string;
  base_type?: string;
  id_type?: string[];
  allowed_values?: string[];
}

interface ManifestKeyring {
  name: string;
  types: string[];
}

interface Manifest {
  version?: string;
  name?: string;
  description?: string;
  functions?: Array<{ name: string; description?: string }>;
  event_sources?: {
    organization?: ManifestEventSource[];
    user?: ManifestEventSource[];
  };
  automations?: Array<{
    name: string;
    source: string;
    event_types?: string[];
    function: string;
  }>;
  commands?: ManifestCommand[];
  operations?: ManifestOperation[];
  hooks?: ManifestHook[];
  snap_kit_actions?: Array<{ name: string; function: string }>;
  inputs?: {
    organization?: ManifestInput[];
    user?: ManifestInput[];
  };
  keyrings?: {
    organization?: ManifestKeyring[];
    user?: ManifestKeyring[];
  };
  tags?: Array<{ name: string; description?: string }>;
}

interface PackageJson {
  name?: string;
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
}

interface ExampleEntry {
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

interface IndexJson {
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
  manifestPatterns: any;
  codePatterns: any;
  useCaseIndex: Record<string, string[]>;
  complexity: Record<string, string[]>;
}

// Constants
const ROOT_DIR = path.resolve(__dirname, '..');
const EXCLUDED_DIRS = ['node_modules', '.git', 'scripts', 'dist'];
const CORE_DEPENDENCIES = ['@devrev/typescript-sdk', 'axios'];

// Snap-in type definitions for classification
const SNAP_IN_TYPE_DEFINITIONS: Record<string, { description: string; detect: (m: Manifest) => boolean }> = {
  'event-driven': {
    description: 'React to DevRev platform events like work_created, work_updated',
    detect: (m) => {
      const sources = [...(m.event_sources?.organization || []), ...(m.event_sources?.user || [])];
      return sources.some(s => s.type === 'devrev-webhook') && (m.automations?.length || 0) > 0;
    }
  },
  'command-based': {
    description: 'Triggered by user slash commands in DevRev UI',
    detect: (m) => (m.commands?.length || 0) > 0
  },
  'timer-based': {
    description: 'Scheduled execution using cron expressions',
    detect: (m) => {
      const sources = [...(m.event_sources?.organization || []), ...(m.event_sources?.user || [])];
      return sources.some(s => s.type === 'timer-events');
    }
  },
  'external-webhook': {
    description: 'Receive and process events from external systems',
    detect: (m) => {
      const sources = [...(m.event_sources?.organization || []), ...(m.event_sources?.user || [])];
      return sources.some(s => s.type === 'flow-custom-webhook');
    }
  },
  'operations': {
    description: 'Reusable actions with defined inputs/outputs',
    detect: (m) => (m.operations?.length || 0) > 0
  },
  'hook-based': {
    description: 'Validate or intercept snap-in lifecycle events',
    detect: (m) => (m.hooks?.length || 0) > 0
  },
  'interactive-ui': {
    description: 'Snap Kit actions for interactive UI elements',
    detect: (m) => (m.snap_kit_actions?.length || 0) > 0
  }
};

// Complexity rules
function determineComplexity(
  manifest: Manifest | null,
  pkg: PackageJson | null,
  features: string[]
): 'beginner' | 'intermediate' | 'advanced' {
  const complexFeatures = ['operations', 'llm-integration', 'multi-function', 'airdrop'];
  const intermediateFeatures = ['snap-kit-actions', 'rego-policy', 'user-level-inputs', 'keyrings', 'external-api'];

  if (features.some(f => complexFeatures.includes(f))) return 'advanced';
  if (features.some(f => intermediateFeatures.includes(f))) return 'intermediate';

  const nonCoreDeps = Object.keys(pkg?.dependencies || {}).filter(d => !CORE_DEPENDENCIES.includes(d));
  if (nonCoreDeps.length > 2) return 'advanced';
  if (nonCoreDeps.length > 0) return 'intermediate';

  return 'beginner';
}

// Feature extraction
function extractFeatures(manifest: Manifest | null, hasSnapKitCode: boolean): string[] {
  const features: string[] = [];

  if (!manifest) {
    if (hasSnapKitCode) features.push('snap-kit-actions');
    return features;
  }

  const sources = [...(manifest.event_sources?.organization || []), ...(manifest.event_sources?.user || [])];

  // Event sources
  for (const source of sources) {
    if (source.type === 'devrev-webhook') features.push('devrev-webhook');
    if (source.type === 'timer-events') {
      features.push('timer-events', 'cron');
    }
    if (source.type === 'flow-custom-webhook') {
      features.push('flow-custom-webhook');
      if (source.config?.policy?.includes('hmac')) features.push('hmac-verification');
      features.push('rego-policy');
    }
    if (source.filter?.jq_query) features.push('jq-filter');
  }

  // Commands
  if (manifest.commands?.length) features.push('commands');

  // Operations
  if (manifest.operations?.length) features.push('operations', 'operation-base-class');

  // Hooks
  if (manifest.hooks?.length) {
    features.push('validate-hook');
    features.push('input-validation');
  }

  // Snap Kit
  if (manifest.snap_kit_actions?.length) features.push('snap-kit-actions');

  // Automations
  if (manifest.automations?.length) features.push('automation');

  // Inputs
  const orgInputs = manifest.inputs?.organization || [];
  const userInputs = manifest.inputs?.user || [];
  if (userInputs.length > 0) features.push('user-level-inputs', 'snap-ins-resources-api');
  for (const input of [...orgInputs, ...userInputs]) {
    if (input.field_type === 'enum') features.push('enum-inputs');
    if (input.field_type === 'id') features.push('id-inputs');
    if (input.field_type === 'array') features.push('array-inputs');
  }

  // Keyrings
  const keyrings = [...(manifest.keyrings?.organization || []), ...(manifest.keyrings?.user || [])];
  if (keyrings.length > 0) features.push('keyrings');
  for (const keyring of keyrings) {
    if (keyring.types.includes('slack')) features.push('slack-integration');
    if (keyring.types.includes('github_connection')) features.push('github-connection');
  }

  // Tags
  if (manifest.tags?.length) features.push('tags');

  return [...new Set(features)];
}

// Learn about topics
function generateLearnAbout(types: string[], features: string[], manifest: Manifest | null): string[] {
  const topics: string[] = [];

  if (types.includes('template')) topics.push('project structure', 'function factory pattern');
  if (features.includes('devrev-webhook')) topics.push('event handling');
  if (features.includes('automation')) topics.push('automations');
  if (features.includes('commands')) topics.push('slash commands');
  if (features.includes('snap-kit-actions')) topics.push('snap kit cards', 'interactive buttons');
  if (features.includes('timer-events')) topics.push('timer events', 'cron scheduling');
  if (features.includes('flow-custom-webhook')) topics.push('external webhooks');
  if (features.includes('rego-policy')) topics.push('Rego policies');
  if (features.includes('hmac-verification')) topics.push('HMAC signature verification');
  if (features.includes('operations')) topics.push('operations pattern', 'OperationBase class');
  if (features.includes('validate-hook')) topics.push('deployment hooks', 'input validation');
  if (features.includes('user-level-inputs')) topics.push('user-scoped inputs', 'per-user configuration');
  if (features.includes('jq-filter')) topics.push('JQ filters');
  if (features.includes('keyrings')) topics.push('keyrings/secrets');
  if (features.includes('tags')) topics.push('tags');
  if (features.includes('enum-inputs')) topics.push('enum inputs');
  if (features.includes('external-api')) topics.push('external API integration');
  if (features.includes('slack-integration')) topics.push('Slack integration');
  if (features.includes('github-connection')) topics.push('GitHub API integration');

  // Add basic topics for simpler examples
  if (manifest?.functions?.length && topics.length < 2) {
    topics.push('timeline entries', 'DevRev SDK usage');
  }

  return [...new Set(topics)];
}

// Find key files in an example
function findKeyFiles(examplePath: string, manifest: Manifest | null): string[] {
  const keyFiles: string[] = [];
  const codePath = path.join(examplePath, 'code', 'src');

  // Manifest
  if (manifest) keyFiles.push('manifest.yaml');

  // Function factory
  const factoryPath = path.join(codePath, 'function-factory.ts');
  if (fs.existsSync(factoryPath)) keyFiles.push('code/src/function-factory.ts');

  // Main entry
  const mainPath = path.join(codePath, 'main.ts');
  if (fs.existsSync(mainPath)) keyFiles.push('code/src/main.ts');

  // Test runner
  const testRunnerPath = path.join(codePath, 'test-runner', 'test-runner.ts');
  if (fs.existsSync(testRunnerPath)) keyFiles.push('code/src/test-runner/test-runner.ts');

  // Functions directory
  const functionsDir = path.join(codePath, 'functions');
  if (fs.existsSync(functionsDir)) {
    const functionDirs = fs.readdirSync(functionsDir, { withFileTypes: true })
      .filter(d => d.isDirectory())
      .map(d => d.name);

    for (const funcDir of functionDirs) {
      const funcIndex = path.join(functionsDir, funcDir, 'index.ts');
      if (fs.existsSync(funcIndex)) {
        keyFiles.push(`code/src/functions/${funcDir}/index.ts`);
      }

      // Check for additional files in function dir (like llm_utils.ts)
      const funcPath = path.join(functionsDir, funcDir);
      const additionalFiles = fs.readdirSync(funcPath)
        .filter(f => f.endsWith('.ts') && f !== 'index.ts' && !f.endsWith('.test.ts'));
      for (const addFile of additionalFiles) {
        keyFiles.push(`code/src/functions/${funcDir}/${addFile}`);
      }
    }
  }

  // Common utilities
  const commonDir = path.join(codePath, 'functions', 'common');
  if (fs.existsSync(commonDir)) {
    const commonFiles = fs.readdirSync(commonDir).filter(f => f.endsWith('.ts'));
    for (const cf of commonFiles) {
      keyFiles.push(`code/src/functions/common/${cf}`);
    }
  }

  return keyFiles;
}

// Generate human-readable name from directory name
function generateName(dirName: string): string {
  // Remove leading number prefix
  const withoutPrefix = dirName.replace(/^\d+-/, '');

  // Special cases
  const nameMap: Record<string, string> = {
    'starter': 'Starter Template',
    'notify-owner-on-ticket-to-prod-assist': 'Notify Owner on Ticket to Prod Assist',
    'giphy-template': 'Giphy Template',
    'sample-snap-in': 'Sample Snap-in',
    'custom-webhook': 'Custom Webhook',
    'timer-ticket-creator': 'Timer Ticket Creator',
    'googleplaystore-reviews-ingestion': 'Google Play Store Reviews Ingestion',
    'external-github-webhook': 'External GitHub Webhook',
    'external-action': 'External Action (GitHub Issues)',
    'vacation-responder': 'Vacation Responder',
    'hook-example': 'Hook Example',
    'csat': 'CSAT Survey',
    'import-airdrop': 'Import Airdrop',
    'operations': 'Operations Example'
  };

  return nameMap[withoutPrefix] || withoutPrefix
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Check if directory contains snap-kit patterns in code
function hasSnapKitInCode(examplePath: string): boolean {
  const codePath = path.join(examplePath, 'code', 'src');
  if (!fs.existsSync(codePath)) return false;

  try {
    const searchInDir = (dir: string): boolean => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.isDirectory() && entry.name !== 'node_modules') {
          if (searchInDir(path.join(dir, entry.name))) return true;
        } else if (entry.isFile() && entry.name.endsWith('.ts')) {
          const content = fs.readFileSync(path.join(dir, entry.name), 'utf-8');
          if (content.includes('snap_kit_body') || content.includes('snap_kit_action')) {
            return true;
          }
        }
      }
      return false;
    };
    return searchInDir(codePath);
  } catch {
    return false;
  }
}

// Main analysis function
function analyzeExample(exampleDir: string): ExampleEntry | null {
  const examplePath = path.join(ROOT_DIR, exampleDir);

  // Read manifest
  let manifest: Manifest | null = null;
  const manifestPath = path.join(examplePath, 'manifest.yaml');
  if (fs.existsSync(manifestPath)) {
    try {
      manifest = yaml.load(fs.readFileSync(manifestPath, 'utf-8')) as Manifest;
    } catch (e) {
      console.warn(`Failed to parse manifest for ${exampleDir}:`, e);
    }
  }

  // Read package.json
  let pkg: PackageJson | null = null;
  const pkgPath = path.join(examplePath, 'code', 'package.json');
  if (fs.existsSync(pkgPath)) {
    try {
      pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
    } catch (e) {
      console.warn(`Failed to parse package.json for ${exampleDir}:`, e);
    }
  }

  // Check for snap-kit in code (for examples without manifest)
  const hasSnapKitCode = hasSnapKitInCode(examplePath);

  // Determine types
  const types: string[] = [];
  if (!manifest) {
    types.push('template');
    if (hasSnapKitCode) types.push('interactive-ui');
  } else {
    for (const [typeName, typeDef] of Object.entries(SNAP_IN_TYPE_DEFINITIONS)) {
      if (typeDef.detect(manifest)) {
        types.push(typeName);
      }
    }
  }
  if (types.length === 0) types.push('specialized');

  // Extract features
  const features = extractFeatures(manifest, hasSnapKitCode);

  // Add feature-based features
  const nonCoreDeps = Object.keys(pkg?.dependencies || {}).filter(d => !CORE_DEPENDENCIES.includes(d));
  if (nonCoreDeps.length > 0) features.push('external-api');

  // Check for test runner
  const testRunnerPath = path.join(examplePath, 'code', 'src', 'test-runner');
  if (fs.existsSync(testRunnerPath)) features.push('test-runner', 'fixture-based-testing');

  // Check for multi-function
  const functionsDir = path.join(examplePath, 'code', 'src', 'functions');
  if (fs.existsSync(functionsDir)) {
    const funcCount = fs.readdirSync(functionsDir, { withFileTypes: true })
      .filter(d => d.isDirectory() && d.name !== 'common').length;
    if (funcCount > 2) features.push('multi-function');

    // Check for common utilities
    if (fs.existsSync(path.join(functionsDir, 'common'))) {
      features.push('common-utilities');
    }
  }

  // Extract event sources and types
  const eventSources: string[] = [];
  const eventTypes: string[] = [];
  let cronExpression: string | undefined;

  if (manifest) {
    const sources = [...(manifest.event_sources?.organization || []), ...(manifest.event_sources?.user || [])];
    for (const source of sources) {
      eventSources.push(source.type);
      if (source.config?.event_types) {
        eventTypes.push(...source.config.event_types);
      }
      if (source.config?.cron) {
        cronExpression = source.config.cron;
      }
    }
  }

  // Extract commands
  const commands = manifest?.commands?.map(c => `/${c.name}`) || [];

  // Extract operations
  const operations = manifest?.operations?.map(o => o.name || o.slug) || [];

  // Extract hook types
  const hookTypes = manifest?.hooks?.map(h => h.type) || [];

  // Determine complexity
  const complexity = determineComplexity(manifest, pkg, features);

  // Get non-core dependencies
  const dependencies = nonCoreDeps.length > 0 ? nonCoreDeps : undefined;

  // Find key files
  const keyFiles = findKeyFiles(examplePath, manifest);

  // Generate learn about topics
  const learnAbout = generateLearnAbout(types, features, manifest);

  // Build entry
  const entry: ExampleEntry = {
    id: exampleDir.replace(/^\d+-/, ''),
    name: generateName(exampleDir),
    path: exampleDir,
    description: manifest?.description || generateDescription(exampleDir, types, features),
    type: types,
    hasManifest: manifest !== null,
    features: [...new Set(features)],
    complexity,
    keyFiles,
    learnAbout
  };

  if (eventSources.length > 0) entry.eventSources = [...new Set(eventSources)];
  if (eventTypes.length > 0) entry.eventTypes = [...new Set(eventTypes)];
  if (commands.length > 0) entry.commands = commands;
  if (operations.length > 0) entry.operations = operations.filter((o): o is string => o !== undefined);
  if (hookTypes.length > 0) entry.hookTypes = hookTypes;
  if (cronExpression) entry.cronExpression = cronExpression;
  if (dependencies) entry.dependencies = dependencies;

  return entry;
}

function generateDescription(dirName: string, types: string[], features: string[]): string {
  const baseName = dirName.replace(/^\d+-/, '');

  const descriptions: Record<string, string> = {
    'starter': 'Minimal template showing basic snap-in structure',
    'csat': 'Post customer satisfaction surveys and process responses',
  };

  if (descriptions[baseName]) return descriptions[baseName];

  // Generate based on features
  const parts: string[] = [];
  if (types.includes('command-based')) parts.push('Command-driven');
  if (types.includes('event-driven')) parts.push('Event-driven');
  if (types.includes('timer-based')) parts.push('Scheduled');
  if (features.includes('external-api')) parts.push('with external API integration');

  return parts.length > 0 ? parts.join(' ') + ' snap-in example' : 'Snap-in example';
}

// Generate manifest patterns section
function generateManifestPatterns(examples: ExampleEntry[]): any {
  return {
    eventSources: {
      'devrev-webhook': {
        description: 'Listen to DevRev platform events',
        eventTypes: ['work_created', 'work_updated', 'conversation_created'],
        scopes: ['organization', 'user'],
        supportsFilters: true,
        exampleFile: '2-notify-owner-on-ticket-to-prod-assist/manifest.yaml'
      },
      'timer-events': {
        description: 'Scheduled execution via cron',
        configFields: ['cron', 'metadata.event_key'],
        exampleFile: '6-timer-ticket-creator/manifest.yaml'
      },
      'flow-custom-webhook': {
        description: 'External webhooks with Rego policy validation',
        configFields: ['policy', 'parameters', 'setup_instructions'],
        exampleFile: '8-external-github-webhook/manifest.yaml'
      }
    },
    inputTypes: {
      text: { description: 'String values', example: 'app_id' },
      bool: { description: 'Boolean flags', example: 'on_vacation' },
      enum: { description: 'Predefined options', example: 'llm_model_to_use' },
      id: { description: 'DevRev object references', idTypes: ['product', 'capability', 'part'] },
      array: { description: 'Lists of values', baseTypes: ['text'] }
    },
    keyrings: {
      types: ['snap_in_secret', 'slack', 'github_connection'],
      scopes: ['organization', 'user', 'operation-level'],
      exampleFile: '7-googleplaystore-reviews-ingestion/manifest.yaml'
    }
  };
}

// Generate code patterns section
function generateCodePatterns(): any {
  return {
    functionFactory: {
      description: 'Central registry mapping function names to implementations',
      location: 'code/src/function-factory.ts',
      pattern: 'export const functionFactory = { func1, func2 } as const;'
    },
    functionSignature: {
      description: 'Standard async function that processes event array',
      pattern: 'export const run = async (events: any[]) => { for (const e of events) await handle(e); };'
    },
    sdkInitialization: {
      description: 'Setup DevRev API client with service account token',
      pattern: 'client.setup({ endpoint: apiBase, token: event.context.secrets.service_account_token })'
    },
    operationBase: {
      description: 'Base class for implementing operations with GetContext() and run()',
      exampleFile: '14-operations/code/src/functions/operation_handler/get_temperature.ts'
    }
  };
}

// Generate use case index
function generateUseCaseIndex(examples: ExampleEntry[]): Record<string, string[]> {
  const useCases: Record<string, (e: ExampleEntry) => boolean> = {
    startNewSnapIn: (e) => e.type.includes('template') && e.id === 'starter',
    reactToDevRevEvents: (e) => e.type.includes('event-driven') && !e.type.includes('command-based'),
    addSlashCommands: (e) => e.type.includes('command-based'),
    createInteractiveUI: (e) => e.type.includes('interactive-ui'),
    receiveExternalWebhooks: (e) => e.type.includes('external-webhook'),
    schedulePeriodicTasks: (e) => e.type.includes('timer-based'),
    integrateExternalAPIs: (e) => e.features.includes('external-api'),
    supportPerUserConfig: (e) => e.features.includes('user-level-inputs'),
    validateBeforeDeployment: (e) => e.type.includes('hook-based'),
    createReusableOperations: (e) => e.type.includes('operations')
  };

  const index: Record<string, string[]> = {};
  for (const [useCase, predicate] of Object.entries(useCases)) {
    index[useCase] = examples.filter(predicate).map(e => e.path);
  }
  return index;
}

// Helper to check if directory is a snap-in (has manifest.yaml or code/ directory)
function isSnapInDir(dirName: string): boolean {
  const dirPath = path.join(ROOT_DIR, dirName);
  const hasManifest = fs.existsSync(path.join(dirPath, 'manifest.yaml'));
  const hasCodeDir = fs.existsSync(path.join(dirPath, 'code'));
  return hasManifest || hasCodeDir;
}

// Main execution
function main() {
  console.log('Scanning snap-in examples...\n');

  // Find all example directories
  const entries = fs.readdirSync(ROOT_DIR, { withFileTypes: true });
  const exampleDirs = entries
    .filter(e => e.isDirectory())
    .filter(e => !EXCLUDED_DIRS.includes(e.name))
    .filter(e => !e.name.startsWith('.')) // Exclude hidden directories
    .filter(e => isSnapInDir(e.name))
    .map(e => e.name)
    .sort((a, b) => {
      // Sort numerically if both have numeric prefixes, otherwise alphabetically
      const numA = parseInt(a.split('-')[0], 10);
      const numB = parseInt(b.split('-')[0], 10);
      if (!isNaN(numA) && !isNaN(numB)) {
        return numA - numB;
      }
      return a.localeCompare(b);
    });

  console.log(`Found ${exampleDirs.length} example directories:\n`);
  exampleDirs.forEach(d => console.log(`  - ${d}`));
  console.log('');

  // Analyze each example
  const examples: ExampleEntry[] = [];
  for (const dir of exampleDirs) {
    console.log(`Analyzing ${dir}...`);
    const entry = analyzeExample(dir);
    if (entry) {
      examples.push(entry);
    }
  }

  // Count deployable vs templates
  const deployable = examples.filter(e => e.hasManifest).length;
  const templates = examples.filter(e => !e.hasManifest).length;

  // Build snap-in types summary
  const snapInTypes: Record<string, { description: string; examples: string[] }> = {};
  for (const [typeName, typeDef] of Object.entries(SNAP_IN_TYPE_DEFINITIONS)) {
    const typeExamples = examples.filter(e => e.type.includes(typeName)).map(e => e.path);
    if (typeExamples.length > 0) {
      snapInTypes[typeName] = {
        description: typeDef.description,
        examples: typeExamples
      };
    }
  }

  // Build complexity index
  const complexityIndex: Record<string, string[]> = {
    beginner: examples.filter(e => e.complexity === 'beginner').map(e => e.path),
    intermediate: examples.filter(e => e.complexity === 'intermediate').map(e => e.path),
    advanced: examples.filter(e => e.complexity === 'advanced').map(e => e.path)
  };

  // Build final index
  const index: IndexJson = {
    repository: {
      name: 'snap-in-examples',
      description: 'Collection of DevRev Snap-in examples demonstrating various patterns and use cases',
      totalExamples: examples.length,
      deployableSnapIns: deployable,
      templates: templates,
      language: 'TypeScript',
      runtime: 'Node.js',
      primarySDK: '@devrev/typescript-sdk',
      generatedAt: new Date().toISOString()
    },
    snapInTypes,
    examples,
    manifestPatterns: generateManifestPatterns(examples),
    codePatterns: generateCodePatterns(),
    useCaseIndex: generateUseCaseIndex(examples),
    complexity: complexityIndex
  };

  // Write output
  const outputPath = path.join(ROOT_DIR, 'index.json');
  fs.writeFileSync(outputPath, JSON.stringify(index, null, 2));

  console.log(`\nGenerated index.json with ${examples.length} examples`);
  console.log(`  - Deployable: ${deployable}`);
  console.log(`  - Templates: ${templates}`);
  console.log(`\nOutput: ${outputPath}`);
}

main();

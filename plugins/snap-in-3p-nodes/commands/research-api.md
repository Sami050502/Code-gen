---
name: research-api
description: Research external API integration patterns, NPM packages, authentication methods, and implementation examples for third-party services
allowed-tools: [Task, AskUserQuestion, Read, Write]
---

# Research API Command

Research external APIs and third-party service integration patterns without going through the full 3P node creation workflow.

## What This Command Does

Provides focused research on external API integration by investigating:
- **Official API documentation** - Endpoints, request/response formats, rate limits
- **NPM packages** - Recommended SDKs and libraries
- **Authentication patterns** - OAuth, API keys, JWT, etc.
- **Code examples** - Real-world implementation patterns

## When to Use This

Use this command when you:
- Need to understand how to integrate with a specific external service
- Want to evaluate integration complexity before committing
- Are troubleshooting existing external API integration
- Need to find the right NPM packages for a service

**Note**: If you want the full workflow (requirements → research → code generation → validation), use `/create-3p-node` instead.

## How to Use

Simply run the command and answer which service you want to research:

```
/research-api
```

The command will ask:
- Which service or API do you want to research? (e.g., Slack, SendGrid, Stripe, GitHub, etc.)
- What specific aspect are you interested in? (authentication, specific endpoints, webhooks, etc.)

## Output

The research agent will provide a structured report containing:

### 1. API Overview
- Service description and use cases
- Base URL and API version
- Rate limits and quotas
- Pricing/tier information

### 2. Authentication
- Authentication method (OAuth 2.0, API Key, JWT, etc.)
- Required credentials and setup steps
- Token refresh patterns (if applicable)
- Security best practices

### 3. NPM Packages
- Official SDKs (if available)
- Community packages (with popularity metrics)
- Recommendation with rationale
- Installation commands

### 4. Key Endpoints
- Commonly used endpoints for the integration
- Request/response examples
- Required parameters
- Error codes

### 5. Implementation Guidance
- Integration patterns for DevRev snap-ins
- How to store credentials (secrets)
- Error handling strategies
- Code examples

### 6. Resources
- Official documentation links
- GitHub repositories
- Tutorial articles
- Community resources

## Example Usage

```
user: /research-api

agent: I'll research an external API for you. Which service or API would you like me to investigate?

user: SendGrid for sending emails

agent: Great! Let me research SendGrid's API...
[Spawns research agent]
[Agent provides comprehensive research report]
```

## Example Output

**Research Report: SendGrid Email API**

**API Overview:**
- Service: SendGrid Email API (v3)
- Base URL: https://api.sendgrid.com/v3
- Purpose: Transactional and marketing email delivery
- Rate limits: Based on plan tier

**Authentication:**
- Method: API Key (Bearer token)
- Setup: Create API key in SendGrid dashboard
- Storage: Store in DevRev snap-in secrets as `SENDGRID_API_KEY`
- Header: `Authorization: Bearer <api_key>`

**Recommended NPM Package:**
```bash
npm install @sendgrid/mail
```
- Official SDK from SendGrid
- 1.5M weekly downloads
- Well-maintained with TypeScript support

**Key Endpoint:**
```
POST /v3/mail/send
```

**Implementation Example:**
```typescript
import sgMail from '@sendgrid/mail';

sgMail.setApiKey(context.secrets.SENDGRID_API_KEY);

const msg = {
  to: 'user@example.com',
  from: 'noreply@yourapp.com',
  subject: 'Ticket Created',
  text: 'Your ticket has been created...',
};

await sgMail.send(msg);
```

**Resources:**
- Docs: https://docs.sendgrid.com/api-reference
- SDK: https://github.com/sendgrid/sendgrid-nodejs
- Examples: [list of example links]

## Related Commands

- `/create-3p-node` - Full workflow including research, generation, and validation
- `/validate-3p-node` - Validate existing 3P node implementation

## Tips

- **Be specific**: Mention the specific service name or API
- **Save the report**: The research output can be referenced when implementing
- **Check npm stats**: Verify package popularity and maintenance status
- **Review security**: Pay attention to authentication and secret management patterns

---

**Implementation Instructions:**

When this command is executed:

1. Use AskUserQuestion to ask which service/API to research
2. Use the Task tool to spawn the research agent with subagent_type="snap-in-3p-nodes:3p-research-agent"
3. Pass the service name and any specific requirements to the agent
4. Display the research report returned by the agent

**Example spawn:**
```
Task tool with:
  subagent_type: "snap-in-3p-nodes:3p-research-agent"
  description: "Research external API"
  prompt: "Research the [SERVICE_NAME] API. Investigate official documentation, recommend NPM packages, document authentication patterns, and provide implementation examples suitable for DevRev snap-ins."
```

# Pact Broker & CI/CD

## What is Pact Broker?

Pact Broker is a central repository that:
- Stores contract (pact) files
- Tracks verification results
- Manages versioning and environments
- Enables `can-i-deploy` safety checks

### Options

1. **Pactflow** (SaaS) — Managed service at pactflow.io
2. **Self-hosted** — Docker image `pactfoundation/pact-broker`

## Publishing Contracts

### From Consumer Tests

After consumer tests run, publish the generated pact files:

```bash
# Using Pact CLI
pact-broker publish ./pacts \
  --broker-base-url=https://your-broker.pactflow.io \
  --broker-token=$PACT_BROKER_TOKEN \
  --consumer-app-version=$GIT_COMMIT \
  --branch=$GIT_BRANCH \
  --tag-with-git-branch
```

### Programmatic Publishing (C#)

```csharp
using PactNet;

public static class PactPublisher
{
    public static async Task PublishAsync()
    {
        var pactDirectory = Path.Combine(Directory.GetCurrentDirectory(), "pacts");
        var brokerUri = new Uri("https://your-broker.pactflow.io");
        var token = Environment.GetEnvironmentVariable("PACT_BROKER_TOKEN")!;
        var version = Environment.GetEnvironmentVariable("GIT_COMMIT") ?? "local";
        var branch = Environment.GetEnvironmentVariable("GIT_BRANCH") ?? "local";

        var publisher = new PactPublisher(brokerUri, new PactPublisherOptions
        {
            TokenAuthentication = token
        });

        await publisher.PublishAsync(
            pactDirectory,
            version,
            new[] { branch });
    }
}
```

### CI Pipeline (GitHub Actions)

```yaml
name: Consumer CI

on:
  push:
    branches: [main, 'feature/**']
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      - name: Run Consumer Pact Tests
        run: dotnet test MyApp.Consumer.Pact

      - name: Publish Pacts
        if: github.event_name == 'push'  # Only on push, not PR
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/tests/MyApp.Consumer.Pact/pacts:/pacts \
            pactfoundation/pact-cli:latest \
            pact-broker publish /pacts \
            --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
            --broker-token=${{ secrets.PACT_BROKER_TOKEN }} \
            --consumer-app-version=${{ github.sha }} \
            --branch=${{ github.ref_name }}
```

## Provider Verification

### Publishing Verification Results

```csharp
verifier
    .WithHttpEndpoint(baseUri)
    .WithPactBrokerSource(new Uri("https://your-broker.pactflow.io"), options =>
    {
        options.TokenAuthentication(Environment.GetEnvironmentVariable("PACT_BROKER_TOKEN")!);
        
        // Publish results back to broker
        options.PublishResults(
            providerVersion: Environment.GetEnvironmentVariable("GIT_COMMIT")!,
            configure: opts => 
            {
                opts.ProviderBranch(Environment.GetEnvironmentVariable("GIT_BRANCH")!);
                opts.ProviderTags(Environment.GetEnvironmentVariable("GIT_BRANCH")!);
            });
        
        // Include pending pacts (new consumers)
        options.EnablePending();
        
        // Which consumer versions to verify
        options.ConsumerVersionSelectors(
            new ConsumerVersionSelector { MainBranch = true },
            new ConsumerVersionSelector { DeployedOrReleased = true }
        );
    })
    .Verify();
```

### CI Pipeline (Provider)

```yaml
name: Provider CI

on:
  push:
    branches: [main, 'feature/**']
  pull_request:
    branches: [main]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      - name: Verify Pacts
        env:
          PACT_BROKER_TOKEN: ${{ secrets.PACT_BROKER_TOKEN }}
          GIT_COMMIT: ${{ github.sha }}
          GIT_BRANCH: ${{ github.ref_name }}
        run: dotnet test MyApp.Provider.Pact
```

## can-i-deploy

### What is can-i-deploy?

`can-i-deploy` answers: "Is it safe to deploy this version?"

It checks:
1. Are all contracts verified?
2. Are the verification results compatible with the target environment?

### Usage

```bash
# Check if consumer can deploy to production
pact-broker can-i-deploy \
  --pacticipant=OrderWebApp \
  --version=$GIT_COMMIT \
  --to-environment=production \
  --broker-base-url=https://your-broker.pactflow.io \
  --broker-token=$PACT_BROKER_TOKEN

# Check if provider can deploy
pact-broker can-i-deploy \
  --pacticipant=OrderGraphQLApi \
  --version=$GIT_COMMIT \
  --to-environment=production \
  --broker-base-url=https://your-broker.pactflow.io \
  --broker-token=$PACT_BROKER_TOKEN
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Safe to deploy |
| 1 | Not safe to deploy |

### CI Integration

```yaml
- name: Can I Deploy?
  run: |
    docker run --rm pactfoundation/pact-cli:latest \
      pact-broker can-i-deploy \
      --pacticipant=OrderWebApp \
      --version=${{ github.sha }} \
      --to-environment=production \
      --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
      --broker-token=${{ secrets.PACT_BROKER_TOKEN }}

- name: Deploy to Production
  if: success()
  run: ./deploy.sh
```

### Dry Run

Check without failing:

```bash
pact-broker can-i-deploy \
  --pacticipant=OrderWebApp \
  --version=$GIT_COMMIT \
  --to-environment=production \
  --dry-run
```

## Recording Deployments

After successful deployment, record it:

```bash
pact-broker record-deployment \
  --pacticipant=OrderWebApp \
  --version=$GIT_COMMIT \
  --environment=production \
  --broker-base-url=https://your-broker.pactflow.io \
  --broker-token=$PACT_BROKER_TOKEN
```

Or for releases (versioned software like mobile apps):

```bash
pact-broker record-release \
  --pacticipant=MobileApp \
  --version=1.2.3 \
  --environment=production
```

## Environments

### Create Environments

```bash
pact-broker create-environment \
  --name=production \
  --display-name="Production" \
  --production

pact-broker create-environment \
  --name=staging \
  --display-name="Staging"
```

## Complete CI/CD Flow

### Consumer Pipeline

```yaml
name: Consumer CI/CD

on:
  push:
    branches: [main]

jobs:
  test-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      # 1. Run consumer tests (generates pact)
      - name: Run Pact Tests
        run: dotnet test MyApp.Consumer.Pact

      # 2. Publish pact to broker
      - name: Publish Pact
        run: |
          docker run --rm \
            -v ./tests/MyApp.Consumer.Pact/pacts:/pacts \
            pactfoundation/pact-cli:latest \
            pact-broker publish /pacts \
            --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
            --broker-token=${{ secrets.PACT_BROKER_TOKEN }} \
            --consumer-app-version=${{ github.sha }} \
            --branch=main

      # 3. Check if safe to deploy
      - name: Can I Deploy?
        run: |
          docker run --rm pactfoundation/pact-cli:latest \
            pact-broker can-i-deploy \
            --pacticipant=OrderWebApp \
            --version=${{ github.sha }} \
            --to-environment=production \
            --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
            --broker-token=${{ secrets.PACT_BROKER_TOKEN }}

      # 4. Deploy
      - name: Deploy
        run: ./deploy-consumer.sh

      # 5. Record deployment
      - name: Record Deployment
        run: |
          docker run --rm pactfoundation/pact-cli:latest \
            pact-broker record-deployment \
            --pacticipant=OrderWebApp \
            --version=${{ github.sha }} \
            --environment=production \
            --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
            --broker-token=${{ secrets.PACT_BROKER_TOKEN }}
```

### Provider Pipeline

```yaml
name: Provider CI/CD

on:
  push:
    branches: [main]

jobs:
  verify-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '8.0.x'

      # 1. Verify pacts (publishes results)
      - name: Verify Pacts
        env:
          PACT_BROKER_TOKEN: ${{ secrets.PACT_BROKER_TOKEN }}
          GIT_COMMIT: ${{ github.sha }}
          GIT_BRANCH: main
        run: dotnet test MyApp.Provider.Pact

      # 2. Check if safe to deploy
      - name: Can I Deploy?
        run: |
          docker run --rm pactfoundation/pact-cli:latest \
            pact-broker can-i-deploy \
            --pacticipant=OrderGraphQLApi \
            --version=${{ github.sha }} \
            --to-environment=production \
            --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
            --broker-token=${{ secrets.PACT_BROKER_TOKEN }}

      # 3. Deploy
      - name: Deploy
        run: ./deploy-provider.sh

      # 4. Record deployment
      - name: Record Deployment
        run: |
          docker run --rm pactfoundation/pact-cli:latest \
            pact-broker record-deployment \
            --pacticipant=OrderGraphQLApi \
            --version=${{ github.sha }} \
            --environment=production \
            --broker-base-url=${{ secrets.PACT_BROKER_URL }} \
            --broker-token=${{ secrets.PACT_BROKER_TOKEN }}
```

## Webhook Triggers

Configure broker to trigger provider verification when new pacts are published:

```bash
pact-broker create-webhook \
  --broker-base-url=https://your-broker.pactflow.io \
  --broker-token=$PACT_BROKER_TOKEN \
  --request-method=POST \
  --url="https://api.github.com/repos/OWNER/REPO/dispatches" \
  --header="Authorization: token $GITHUB_TOKEN" \
  --header="Accept: application/vnd.github.v3+json" \
  --data='{"event_type":"pact_changed","client_payload":{"pact_url":"${pactbroker.pactUrl}"}}' \
  --contract-content-changed \
  --provider=OrderGraphQLApi
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| can-i-deploy fails | No verification results | Run provider verification first |
| "Unknown participant" | Typo in name | Check exact pacticipant name in broker |
| Pending pacts not verified | `EnablePending()` not set | Add to provider verification |
| Old pacts verified | Wrong selectors | Use `DeployedOrReleased` selector |

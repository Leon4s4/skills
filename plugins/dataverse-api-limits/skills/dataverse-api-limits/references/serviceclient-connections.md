# Connect with ServiceClient

How to connect to Dataverse with the modern .NET client,
`Microsoft.PowerPlatform.Dataverse.Client.ServiceClient`. This client implements
`IOrganizationService` and **auto-handles service protection 429s** (pauses for
`Retry-After` then resends) — so preferring it is the simplest way to get correct
retry behavior. See [error-codes-and-limits.md](error-codes-and-limits.md) and
[throughput-and-parallelism.md](throughput-and-parallelism.md) for the limits it
manages.

## Contents
- [Packages & class lineage](#packages--class-lineage)
- [Supported frameworks & auth types](#supported-frameworks--auth-types)
- [Minimal quickstart](#minimal-quickstart)
- [Connection string parameters](#connection-string-parameters)
- [Connection string examples](#connection-string-examples)
- [Check connection status](#check-connection-status)
- [Execute operations](#execute-operations)
- [Security](#security)

## Packages & class lineage

- **NuGet:** `Microsoft.PowerPlatform.Dataverse.Client` (and
  `Microsoft.PowerPlatform.Dataverse.Client.Dynamics`). Install the latest version.
- `ServiceClient` is the current, recommended client — a revision of the older
  `Microsoft.Xrm.Tooling.Connector.CrmServiceClient` and underlying
  `Microsoft.Xrm.Sdk.Client` libraries.
- **Migrate off** the low-level, deprecated `OrganizationServiceProxy` /
  `OrganizationWebProxyClient` → use `ServiceClient`. Transition guide:
  `power-apps/developer/data-platform/sdk-client-transition`.
- **Plugin/custom-workflow-activity development is NOT supported** with this client.
- The repo cannot be built outside Microsoft (internal-only package dependencies);
  consume it via NuGet, not source.

## Supported frameworks & auth types

Target frameworks: .NET Framework 4.6.2 / 4.7.2 / 4.8, and .NET Core 3.0 / 3.1 / 5.0 / 6.0+.

Permitted auth types for Dataverse: `OAuth`, `Certificate`, `ClientSecret`,
`Office365` (deprecated — use `OAuth`). `AD`/`IFD` apply only to on-prem.

| Auth type | .NET Framework | .NET Core |
| --- | --- | --- |
| ClientSecret (S2S) | ✅ | ✅ |
| Certificate (S2S) | ✅ | ✅ |
| UID/PW interactive (OAuth) | ✅ | ✅ |
| UID/PW non-interactive (OAuth) | ✅ | ❌ |

For unattended/server scenarios prefer **ClientSecret** or **Certificate** (app
registration / service principal). Same service protection limits apply to
application users as to interactive users.

## Minimal quickstart

Install `Microsoft.PowerPlatform.Dataverse.Client`, then:

```csharp
using Microsoft.Crm.Sdk.Messages;
using Microsoft.PowerPlatform.Dataverse.Client;
using Microsoft.Xrm.Sdk;

string connectionString = @"
   AuthType = OAuth;
   Url = https://yourorg.crm.dynamics.com;
   UserName = you@yourorg.onmicrosoft.com;
   Password = yourPassword;
   AppId = 51f81489-12ee-4a9e-aaae-a2591f45987d;
   RedirectUri = app://58145B91-0C36-4500-8554-080854F2AC97;
   LoginPrompt = Auto;
   RequireNewInstance = True";

// ServiceClient implements IOrganizationService
IOrganizationService service = new ServiceClient(connectionString);

var response = (WhoAmIResponse)service.Execute(new WhoAmIRequest());
Console.WriteLine($"User ID is {response.UserId}.");
```

> The `AppId` / `RedirectUri` above are Microsoft-provided **sample** values for
> dev/prototyping only. For production, register your own app in Microsoft Entra ID.

## Connection string parameters

Semicolon-separated `name=value` pairs (order-independent):

| Parameter (aliases) | Purpose |
| --- | --- |
| `Url` (`ServiceUri`, `Service Uri`, `Server`) | Environment URL, e.g. `https://<org>.crm.dynamics.com` (required) |
| `AuthType` (`AuthenticationType`) | `OAuth` \| `Certificate` \| `ClientSecret` \| `Office365` (deprecated) |
| `UserName` (`User Name`, `UserId`, `User Id`) | User identity (UID/PW flows) |
| `Password` | Password (UID/PW flows) |
| `ClientId` (`AppId`, `ApplicationId`) | Entra ID / AD FS app registration ID |
| `ClientSecret` (`Secret`) | Required when `AuthType=ClientSecret` |
| `Thumbprint` (`CertThumbprint`) | Cert thumbprint for S2S; requires `AppId`; ignores UID/PW |
| `StoreName` (`CertificateStoreName`) | Cert store name; requires `Thumbprint` |
| `RedirectUri` (`ReplyUrl`) | OAuth redirect URI |
| `LoginPrompt` | OAuth: `Always` \| `Auto` \| `Never` (use `Never` for headless) |
| `TokenCacheStorePath` | OAuth token cache file path |
| `Integrated Security` | Use current Windows credentials (9.1.0.21+) |
| `RequireNewInstance` | `true` = new unique connection; `false` = reuse active connection |
| `HomeRealmUri` | Home Realm URI (federation) |

Access connection strings from config with `using System.Configuration;`.

## Connection string examples

OAuth, named account, interactive prompt (preferred interactive flow; supports
Conditional Access + MFA):
```
AuthType=OAuth;Username=jsmith@contoso.onmicrosoft.com;Password=passcode;
Url=https://contoso.crm.dynamics.com;AppId=51f81489-12ee-4a9e-aaae-a2591f45987d;
RedirectUri=app://58145B91-0C36-4500-8554-080854F2AC97;
TokenCacheStorePath=c:\MyTokenCache;LoginPrompt=Auto
```

OAuth, current Windows user (`Integrated Security=true`):
```
AuthType=OAuth;Username=jsmith@contoso.onmicrosoft.com;Integrated Security=true;
Url=https://contoso.crm.dynamics.com;AppId=51f81489-12ee-4a9e-aaae-a2591f45987d;
RedirectUri=app://58145B91-0C36-4500-8554-080854F2AC97;LoginPrompt=Auto
```

Certificate (S2S):
```
AuthType=Certificate;Url=https://contoso.crm.dynamics.com;
thumbprint={CertThumbPrintId};ClientId={AppId};
```

ClientSecret (S2S):
```
AuthType=ClientSecret;Url=https://contoso.crm.dynamics.com;
ClientId={AppId};ClientSecret={ClientSecret}
```

Office365 (**deprecated** — migrate to `OAuth`):
```
AuthType=Office365;Username=jsmith@contoso.onmicrosoft.com;Password=passcode;
Url=https://contoso.crm.dynamics.com
```

## Check connection status

After constructing the client, confirm `IsReady == true` before using it. On
failure, inspect the last-error properties:
- `ServiceClient`: `IsReady`, `LastError`, `LastException`.
- `CrmServiceClient`: `IsReady`, `LastCrmError`, `LastCrmException`.

## Execute operations

`ServiceClient` implements `IOrganizationService` — `Create`, `Retrieve`,
`Update`, `Delete`, `RetrieveMultiple`, `Associate`, `Disassociate`, and `Execute`
(for message requests like `WhoAmIRequest`). It also offers async variants
(`CreateAsync`, etc. — use these with `Parallel.ForEachAsync`; see
[throughput-and-parallelism.md](throughput-and-parallelism.md)), extension methods
beyond `IOrganizationService`, and `ILogger` logging support.

For bulk work, set `EnableAffinityCookie = false` and drive parallelism from
`RecommendedDegreesOfParallelism`. On .NET Framework, use `Clone()` per thread.

## Security

Microsoft recommends the most secure auth flow available; prefer **managed
identities** where viable, then `Certificate`/`ClientSecret` for S2S. UID/PW
connection strings require very high trust and carry extra risk. Never hard-code
secrets — store them in `app.config`/`web.config`/`appsettings.json` (encrypt
config sections) or a secret store, and protect any file holding credentials.

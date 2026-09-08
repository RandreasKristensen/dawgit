# Git for Music — Architecture Reference

> We host the collaboration. You own the files.

This is the single consolidated reference for the Git for Music platform: the product
framing, the intended repository structure, the component responsibilities, and the
full set of architecture diagrams. 

**Status:** this document describes the target platform architecture. Only the
`core/` directory (the Rust versioning engine) currently exists in this repository —
see [`core/MVP.md`](../core/MVP.md) and [`core/Requirements.md`](../core/Requirements.md)
for what is actually being built right now and why the rest is deliberately not yet
scaffolded.

## Product framing

Git for Music is a cross-platform system for versioning and sharing music production
projects (DAW projects, stems, samples). It is built around three ideas:

1. **Content lives on the user's device, not in the cloud.** Project files, audio,
   and version history are stored locally and synchronized directly between
   collaborators' devices (peer-to-peer). The cloud never persists project content.
2. **The cloud is a coordination layer only.** A proprietary C# backend handles
   identity, project/collaborator metadata, permissions, device presence, and P2P
   rendezvous — but not file content. It lives in a separate, private repository and
   is not implemented here.
3. **A local versioning engine, written in Rust, is the foundation.** It owns
   content-addressed storage, history, and P2P synchronization, and exposes a stable
   C-compatible API so it can be embedded in different shells (CLI, desktop app,
   future DAW plugin).

## Repository components

The platform is designed around five logical components. Today, only the first is
present in this repository; the rest describe where the project is headed.

| Component | Responsibility | Status |
| --- | --- | --- |
| `core` (Rust) | Local storage, content-addressed versioning, and P2P synchronization engine | **In this repository.** See [`core/MVP.md`](../core/MVP.md) and [`core/Requirements.md`](../core/Requirements.md). |
| `frontend` (Angular) | Presentation layer for the desktop/web client | Not in this repository yet. Deferred until the core versioning engine is proven standalone. |
| `protocol` | Shared wire protocol for peer identity, sync sessions, object negotiation/transfer, integrity verification, and reference updates | Not in this repository yet. Will be extracted once the core's in-process sync protocol is stable enough to need a formal, versioned contract. |
| `infra` | Repository-local infrastructure for the open-source client (packaging, CI, etc.) | Not in this repository yet. |
| Cloud backend (C#) | Identity, project/permission metadata, device presence, sync coordination, billing | Proprietary, maintained in a separate repository. Represented here only as an architecture boundary — see the diagrams below. |

The C++/JUCE native integration layer (the desktop shell that hosts the Angular UI
and calls into the Rust core) is also represented in the diagrams but is not
implemented in this repository.

### Why the repository is scoped to `core/` right now

The project was documentation-heavy relative to what had been built: nine diagrams
and five component READMEs existed before any code did. The repository has been
deliberately narrowed to just the Rust core so that the hardest and most
foundational open question — whether content-addressed versioning and diff/merge
are viable for real, mostly-binary DAW project files — gets answered before
networking, cloud, and UI work begins. See [`core/MVP.md`](../core/MVP.md).

### Longer-term repository evolution

Once the core is proven, the project is expected to grow through repository-structure
stages, splitting only when ownership, access control, release cadence, or API
stability actually require it — not by programming language alone:

1. **Monorepo:** build initial vertical slices for Rust, C#, Angular, protocol
   contracts, and local infrastructure together while boundaries are still changing.
2. **Three repositories:** separate `gitformusic-core` (Rust), `gitformusic-backend`
   (C#), and `gitformusic-desktop` (Angular + desktop integration) once their release
   cadences diverge.
3. **Five repositories:** split out `gitformusic-protocol` and
   `gitformusic-infrastructure` once their ownership and compatibility policies are
   stable enough to version independently.

The repository should stay in the simplest stage that supports current development —
right now, that stage is "core only," a step even before stage 1.

## Diagrams

All diagrams share one Mermaid theme (light blue, defined by the `%%{init: ...}%%`
directive embedded at the top of each block below) so any new diagram added to this
document should reuse the same directive for visual consistency.

### Architecture overview

Control plane (C#/GraphQL) vs. data plane (Rust core), and the direct P2P link
between peers' data planes.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% Music Project Platform - Architecture Overview
flowchart TB

    subgraph BACKGROUND

    PLATFORM["Music Project Platform"]

    subgraph CONTROL["Control Plane"]
        GRAPHQL["C# / GraphQL"]
        IDENTITY["Identity"]
        PROJECTS["Projects"]
        PERMISSIONS["Permissions"]
        DEVICES["Devices"]
        COORDINATION["Coordination"]
        BILLING["Billing"]

        GRAPHQL --- IDENTITY
        GRAPHQL --- PROJECTS
        GRAPHQL --- PERMISSIONS
        GRAPHQL --- DEVICES
        GRAPHQL --- COORDINATION
        GRAPHQL --- BILLING
    end

    subgraph DATA["Data Plane"]
        RUST["Rust Core"]
        VERSIONING["Versioning"]
        OBJECT_STORE["Object Store"]
        P2P_SYNC["P2P Sync"]
        CRYPTO["Crypto"]
        FILESYSTEM["Filesystem"]

        RUST --- VERSIONING
        RUST --- OBJECT_STORE
        RUST --- P2P_SYNC
        RUST --- CRYPTO
        RUST --- FILESYSTEM
    end

    OTHER_RUST["Other User's Rust Core"]
    QUESTION["Who can access what, and how do we find each other?"]

    PLATFORM --> CONTROL
    PLATFORM --> DATA
    CONTROL --> QUESTION
    DATA -->|"direct P2P"| OTHER_RUST

    end
    style BACKGROUND fill:#ffffff,stroke:#ffffff,stroke-width:1px
```

### Dependency direction

Angular, JUCE, FFI, and Rust dependency flow, and what the Rust core's own
capabilities (filesystem, network, crypto) are ultimately in service of.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% Music Project Platform - Dependency Direction
flowchart TB

    subgraph BACKGROUND

    ANGULAR["Angular UI"]
    JUCE["C++ / JUCE"]
    FFI["C API / FFI"]
    RUST["Rust Core"]

    subgraph CAPABILITIES["Rust Core Capabilities"]
        FILESYSTEM["Filesystem"]
        NETWORK["Network"]
        CRYPTO["Crypto"]
    end

    USER_DATA["User Data"]
    P2P["P2P"]
    SECURITY["Security"]

    ANGULAR --> JUCE
    JUCE --> FFI
    FFI --> RUST

    RUST --> FILESYSTEM
    RUST --> NETWORK
    RUST --> CRYPTO

    FILESYSTEM --> USER_DATA
    NETWORK --> P2P
    CRYPTO --> SECURITY

    end
    style BACKGROUND fill:#ffffff,stroke:#ffffff,stroke-width:1px
```

### System overview

Two client devices, cloud coordination, local stores, and the P2P transfer path
between them.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% Music Versioning Platform — System Overview
flowchart TB

    subgraph BACKGROUND

    %% =========================================================
    %% CLIENT DEVICES
    %% =========================================================

    subgraph CLIENT_A["User Device A"]
        direction TB

        DAW_A["DAW / Music Software"]

        subgraph DESKTOP_A["Music Versioning Client"]
            direction TB

            ANGULAR_A["Angular Desktop UI"]
            JUCE_A["C++ / JUCE Integration Layer"]
            RUST_A["Rust Core"]

            ANGULAR_A -->|"controls and observes"| JUCE_A
            JUCE_A -->|"invokes core operations"| RUST_A
        end

        LOCAL_FS_A[("Local Project Files")]
        LOCAL_STORE_A[("Local Content-Addressed Object Store")]

        DAW_A -->|"creates and modifies"| LOCAL_FS_A
        RUST_A -->|"reads and versions"| LOCAL_FS_A
        RUST_A -->|"stores immutable objects"| LOCAL_STORE_A
    end


    subgraph CLIENT_B["User Device B"]
        direction TB

        DAW_B["DAW / Music Software"]

        subgraph DESKTOP_B["Music Versioning Client"]
            direction TB

            ANGULAR_B["Angular Desktop UI"]
            JUCE_B["C++ / JUCE Integration Layer"]
            RUST_B["Rust Core"]

            ANGULAR_B -->|"controls and observes"| JUCE_B
            JUCE_B -->|"invokes core operations"| RUST_B
        end

        LOCAL_FS_B[("Local Project Files")]
        LOCAL_STORE_B[("Local Content-Addressed Object Store")]

        DAW_B -->|"creates and modifies"| LOCAL_FS_B
        RUST_B -->|"reads and versions"| LOCAL_FS_B
        RUST_B -->|"stores immutable objects"| LOCAL_STORE_B
    end


    %% =========================================================
    %% CLOUD
    %% =========================================================

    subgraph CLOUD["Cloud Platform"]
        direction TB

        subgraph API["Application API"]
            GRAPHQL["GraphQL API Gateway"]
            AUTH["Authentication Service"]
            PROJECT["Project Metadata Service"]
            COLLAB["Collaboration & Permission Service"]
            DEVICE["Device Registry & Presence Service"]
            SYNC["Sync Coordination Service"]
            NOTIFY["Notification Service"]
            BILLING["Billing Service"]
        end

        subgraph DATA["Cloud Data Stores"]
            DB[("PostgreSQL\nMetadata Database")]
            CACHE[("Redis\nCache / Presence")]
        end

        subgraph NETWORK["P2P Connectivity Infrastructure"]
            RENDEZVOUS["Peer Rendezvous Service"]
            RELAY["Encrypted P2P Relay"]
        end

        GRAPHQL -->|"authenticates requests"| AUTH
        GRAPHQL -->|"reads and mutates project metadata"| PROJECT
        GRAPHQL -->|"manages collaborators and permissions"| COLLAB
        GRAPHQL -->|"queries device availability"| DEVICE
        GRAPHQL -->|"creates synchronization sessions"| SYNC
        GRAPHQL -->|"manages notifications"| NOTIFY
        GRAPHQL -->|"manages subscriptions and payments"| BILLING

        AUTH -->|"persists account identity"| DB
        PROJECT -->|"persists project metadata"| DB
        COLLAB -->|"persists access rules"| DB
        DEVICE -->|"stores short-lived presence"| CACHE
        SYNC -->|"persists synchronization metadata"| DB

        DEVICE -->|"registers reachable devices"| RENDEZVOUS
        SYNC -->|"requests peer connection"| RENDEZVOUS
        RENDEZVOUS -->|"provides connection candidates"| RUST_A
        RENDEZVOUS -->|"provides connection candidates"| RUST_B
    end


    %% =========================================================
    %% WEB FRONTEND
    %% =========================================================

    WEB["Angular Web Application"]

    WEB -->|"queries and mutates application state"| GRAPHQL


    %% =========================================================
    %% CLIENT ↔ CLOUD
    %% =========================================================

    RUST_A -->|"authenticates and registers device"| GRAPHQL
    RUST_A -->|"publishes device presence"| DEVICE
    RUST_A -->|"requests synchronization session"| SYNC

    RUST_B -->|"authenticates and registers device"| GRAPHQL
    RUST_B -->|"publishes device presence"| DEVICE
    RUST_B -->|"requests synchronization session"| SYNC


    %% =========================================================
    %% P2P DATA PLANE
    %% =========================================================

    RUST_A <-->|"synchronizes missing objects\nusing encrypted P2P transport"| RUST_B

    RUST_A -.->|"falls back to encrypted byte relay"| RELAY
    RUST_B -.->|"falls back to encrypted byte relay"| RELAY


    %% =========================================================

    end
    style BACKGROUND fill:#ffffff,stroke:#ffffff,stroke-width:1px
```

### Rust core

Core interfaces, versioning, storage, synchronization, networking, and cryptography
— the full internal design of the component that is now the sole focus of this
repository. See [`core/Requirements.md`](../core/Requirements.md) for how this maps
to concrete requirements, and [`core/MVP.md`](../core/MVP.md) for what subset is
being built first.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% Rust Core — Local Versioning and Synchronization Engine
flowchart TB

    subgraph BACKGROUND

    %% =========================================================
    %% PUBLIC INTERFACE
    %% =========================================================

    subgraph INTERFACE["Core Interfaces"]
        direction LR

        CLI["Rust CLI"]
        FFI["C-Compatible FFI API"]
        DAEMON["Local Core Daemon"]
    end


    %% =========================================================
    %% APPLICATION SERVICES
    %% =========================================================

    subgraph APPLICATION["Application Services"]
        direction TB

        REPO["Repository Service"]
        VERSION["Versioning Service"]
        CHECKOUT["Checkout Service"]
        STATUS["Working Tree Status Service"]
        DIFF["Diff Service"]
        GC["Garbage Collection Service"]
    end


    %% =========================================================
    %% OBJECT MODEL
    %% =========================================================

    subgraph OBJECTS["Content-Addressed Version Model"]
        direction TB

        HASH["Hashing Engine"]

        BLOB["Blob Objects\nFile Contents"]
        TREE["Tree Objects\nDirectory Structure"]
        COMMIT["Commit Objects\nProject Snapshots"]
        REF["Reference Manager\nBranches / HEAD / Tags"]

        HASH -->|"identifies"| BLOB
        HASH -->|"identifies"| TREE
        HASH -->|"identifies"| COMMIT

        TREE -->|"references"| BLOB
        COMMIT -->|"references root"| TREE
        REF -->|"points to"| COMMIT
    end


    %% =========================================================
    %% OBJECT STORAGE
    %% =========================================================

    subgraph STORAGE["Local Object Storage"]
        direction TB

        OBJECT_STORE["Object Store"]
        INDEX["Object Index"]
        PACK["Packfile / Compression Layer"]
        CHUNK["Chunk Store\nFuture Optimization"]
        LOCK["Repository Lock Manager"]

        OBJECT_STORE -->|"indexes objects"| INDEX
        OBJECT_STORE -->|"optionally packs objects"| PACK
        OBJECT_STORE -.->|"may store large content as chunks"| CHUNK
        LOCK -->|"protects repository mutations"| OBJECT_STORE
    end


    %% =========================================================
    %% WORKING TREE
    %% =========================================================

    subgraph WORKTREE["Working Tree"]
        direction TB

        FS["Filesystem Scanner"]
        WATCHER["Filesystem Watcher"]
        MANIFEST["Working Tree Manifest"]
        MATERIALIZER["Checkout / Materialization Engine"]

        FS -->|"enumerates project files"| MANIFEST
        WATCHER -->|"detects filesystem changes"| MANIFEST
        MANIFEST -->|"compares against committed tree"| STATUS
        MATERIALIZER -->|"writes selected version"| FS
    end


    %% =========================================================
    %% SYNC
    %% =========================================================

    subgraph SYNC_ENGINE["Synchronization Engine"]
        direction TB

        PEER["Peer Identity Manager"]
        DISCOVERY["Peer Discovery Client"]
        SESSION["Sync Session Manager"]
        NEGOTIATION["Object Inventory & Negotiation"]
        TRANSFER["Object Transfer Engine"]
        RESUME["Transfer Resume Manager"]
        VERIFY["Integrity Verification"]
        PROTOCOL["P2P Protocol"]

        PEER -->|"authenticates peer"| SESSION
        DISCOVERY -->|"finds reachable peers"| SESSION
        SESSION -->|"negotiates synchronization"| NEGOTIATION
        NEGOTIATION -->|"requests missing objects"| TRANSFER
        TRANSFER -->|"resumes interrupted transfers"| RESUME
        TRANSFER -->|"verifies received bytes"| VERIFY
        SESSION -->|"communicates using"| PROTOCOL
    end


    %% =========================================================
    %% NETWORK
    %% =========================================================

    subgraph NETWORKING["Network Transport"]
        direction TB

        TCP["TCP Transport\nMVP"]
        QUIC["QUIC Transport\nFuture"]
        NAT["NAT Traversal\nFuture"]
        RELAY_CLIENT["Encrypted Relay Client\nFuture"]
    end


    %% =========================================================
    %% CRYPTO
    %% =========================================================

    subgraph CRYPTO["Cryptography"]
        direction TB

        KEYSTORE["Local Key Store"]
        IDENTITY["Device Identity"]
        SIGN["Commit / Message Signing"]
        AEAD["Authenticated Encryption"]
        TLS["Transport Security"]
    end


    %% =========================================================
    %% CONNECTIONS
    %% =========================================================

    CLI -->|"executes commands"| REPO
    FFI -->|"exposes core operations"| REPO
    DAEMON -->|"hosts long-running services"| REPO

    REPO -->|"creates and opens"| VERSION
    VERSION -->|"creates immutable versions"| COMMIT
    VERSION -->|"updates references"| REF

    REPO -->|"reads and writes"| OBJECT_STORE

    CHECKOUT -->|"materializes commit"| MATERIALIZER
    STATUS -->|"reads working tree state"| MANIFEST
    DIFF -->|"compares versions"| TREE
    GC -->|"removes unreachable objects"| OBJECT_STORE

    VERSION -->|"stores objects"| OBJECT_STORE
    COMMIT -->|"references"| TREE
    TREE -->|"references"| BLOB

    SYNC_ENGINE -->|"reads local inventory"| OBJECT_STORE
    SYNC_ENGINE -->|"writes received objects"| OBJECT_STORE

    TRANSFER -->|"stores verified objects"| OBJECT_STORE

    PROTOCOL -->|"runs over"| TCP
    PROTOCOL -.->|"future transport"| QUIC
    QUIC -.->|"attempts direct connectivity"| NAT
    NAT -.->|"falls back when necessary"| RELAY_CLIENT

    PEER -->|"uses cryptographic identity"| IDENTITY
    IDENTITY -->|"stores keys in"| KEYSTORE
    SIGN -->|"signs trusted metadata"| IDENTITY
    PROTOCOL -->|"secures communication with"| TLS
    TRANSFER -->|"protects payloads with"| AEAD

    %% =========================================================

    end
    style BACKGROUND fill:#ffffff,stroke:#ffffff,stroke-width:1px
```

### Cloud backend (reference only)

Proprietary C# service domains and persistent infrastructure. This is reference
architecture only — it documents the boundary the Rust core talks to; it is not
implemented in this repository and is maintained privately.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% Cloud Platform - C# Backend Services
flowchart TB

    subgraph BACKGROUND

    CLIENT["Angular Web Client"]
    RUST["Rust Core on User Device"]

    subgraph API["API Layer"]
        GRAPHQL["GraphQL API Gateway"]
        WS["Realtime Event Gateway"]
    end

    subgraph DOMAINS["Backend Service Domains"]
        direction TB

        subgraph IDENTITY["Identity"]
            AUTH["Authentication"]
            SESSION["Session"]
            TOKEN["Token"]
            USER["User Profile"]
        end

        subgraph PROJECTS["Projects"]
            PROJECT["Project"]
            MEMBERSHIP["Membership"]
            PERMISSION["Permission"]
            COMMIT_META["Commit Metadata"]
            BRANCH["Branch Metadata"]
        end

        subgraph DEVICES["Devices and Connectivity"]
            DEVICE["Device Registry"]
            PRESENCE["Device Presence"]
            RENDEZVOUS["Peer Rendezvous"]
            SYNC_COORD["Sync Coordination"]
        end

        subgraph COLLAB["Collaboration"]
            INVITE["Invitation"]
            ACTIVITY["Activity Feed"]
            NOTIFICATION["Notification"]
        end

        subgraph COMMERCE["Commerce"]
            SUBSCRIPTION["Subscription"]
            BILLING["Billing"]
            ENTITLEMENT["Entitlement"]
        end
    end

    subgraph DATA["Persistent Infrastructure"]
        POSTGRES[("PostgreSQL")]
        REDIS[("Redis")]
        QUEUE[("Message Queue")]
    end

    CLIENT --> GRAPHQL
    CLIENT --> WS
    RUST --> GRAPHQL
    RUST --> WS

    GRAPHQL --> AUTH
    GRAPHQL --> USER
    GRAPHQL --> PROJECT
    GRAPHQL --> MEMBERSHIP
    GRAPHQL --> PERMISSION
    GRAPHQL --> COMMIT_META
    GRAPHQL --> BRANCH
    GRAPHQL --> DEVICE
    GRAPHQL --> PRESENCE
    GRAPHQL --> RENDEZVOUS
    GRAPHQL --> SYNC_COORD
    GRAPHQL --> INVITE
    GRAPHQL --> ACTIVITY
    GRAPHQL --> NOTIFICATION
    GRAPHQL --> SUBSCRIPTION
    GRAPHQL --> BILLING
    GRAPHQL --> ENTITLEMENT

    DEVICE -->|"presence events"| WS
    SYNC_COORD -->|"sync events"| WS
    NOTIFICATION -->|"user events"| WS

    AUTH --> POSTGRES
    SESSION --> POSTGRES
    TOKEN --> POSTGRES
    USER --> POSTGRES
    PROJECT --> POSTGRES
    MEMBERSHIP --> POSTGRES
    PERMISSION --> POSTGRES
    COMMIT_META --> POSTGRES
    BRANCH --> POSTGRES
    DEVICE --> POSTGRES
    PRESENCE --> REDIS
    SYNC_COORD --> POSTGRES
    ACTIVITY --> POSTGRES
    NOTIFICATION --> QUEUE
    SUBSCRIPTION --> POSTGRES
    BILLING --> POSTGRES
    ENTITLEMENT --> POSTGRES

    MEMBERSHIP -->|"access"| PERMISSION
    PROJECT -->|"access"| PERMISSION
    SYNC_COORD -->|"permission check"| PERMISSION
    SYNC_COORD -->|"online devices"| PRESENCE
    SYNC_COORD -->|"connection request"| RENDEZVOUS

    end
    style BACKGROUND fill:#ffffff,stroke:#ffffff,stroke-width:1px
```

### P2P synchronization

Missing-object transfer sequence between two Rust cores, coordinated (but not
witnessed in content) by the cloud.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% P2P Synchronization — Missing Object Transfer
sequenceDiagram

    rect rgb(255, 255, 255)

    participant UI_A as User A / Angular UI
    participant RA as Rust Core A
    participant CLOUD as Sync Coordination Service
    participant RD as Rust Core B
    participant OS_A as Object Store A
    participant OS_B as Object Store B

    UI_A->>RA: Request project synchronization

    RA->>CLOUD: Request sync session for Project X

    CLOUD->>CLOUD: Authenticate User A
    CLOUD->>CLOUD: Verify Project X permissions
    CLOUD->>CLOUD: Locate reachable Device B

    CLOUD-->>RA: Return peer identity + connection candidates
    CLOUD-->>RD: Notify Device B of incoming sync

    RA->>RD: Establish authenticated P2P session

    RA->>OS_A: Read target commit
    RD->>OS_B: Read current commit

    RA->>RD: Advertise target commit + object inventory
    RD->>RA: Advertise existing object inventory

    RA->>RA: Calculate missing object set

    loop For each missing object
        RA->>RD: Request / send object
        RA->>RD: Stream object bytes
        RD->>RD: Hash received bytes
        RD->>RD: Verify object identifier
        RD->>OS_B: Atomically store verified object
        RD-->>RA: Confirm object receipt
    end

    RA->>RD: Send reference update
    RD->>RD: Verify referenced commit
    RD->>OS_B: Update local reference

    RD-->>CLOUD: Report synchronization completed
    CLOUD-->>UI_A: Publish synchronization result

    Note over RA,RD: Project contents are never persistently stored by the cloud.

    end
```

### Data ownership and storage

What lives on the user's device, what lives in the cloud, and what never crosses
that boundary.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% Data Ownership and Storage Boundaries
flowchart LR

    subgraph BACKGROUND

    subgraph USER_DEVICE["User Device"]
        direction TB

        PROJECT_FILES["Music Project Files"]
        AUDIO["Audio / Stems / Samples"]
        OBJECTS["Content-Addressed Objects"]
        HISTORY["Version History"]
        KEYS["Private Device Keys"]
        CONFIG["Local Configuration"]
    end


    subgraph CLOUD["Cloud Platform"]
        direction TB

        ACCOUNT["Account Identity"]
        PROJECT_META["Project Metadata"]
        MEMBERS["Collaborators & Permissions"]
        COMMIT_META["Commit Metadata"]
        DEVICE_META["Device Registration"]
        PRESENCE["Ephemeral Device Presence"]
        BILLING["Subscription / Billing State"]
        NOTIFICATIONS["Notification State"]
    end


    subgraph PEER["Other User Device"]
        direction TB

        PEER_FILES["Music Project Files"]
        PEER_OBJECTS["Content-Addressed Objects"]
        PEER_HISTORY["Version History"]
        PEER_KEYS["Private Device Keys"]
    end


    PROJECT_FILES -->|"is versioned into"| OBJECTS
    AUDIO -->|"is versioned into"| OBJECTS
    HISTORY -->|"is represented by"| OBJECTS

    OBJECTS <-->|"synchronizes directly"| PEER_OBJECTS
    HISTORY <-->|"synchronizes through commits"| PEER_HISTORY

    ACCOUNT -->|"authorizes"| PROJECT_META
    PROJECT_META -->|"defines"| MEMBERS
    PROJECT_META -->|"references"| COMMIT_META
    DEVICE_META -->|"describes"| USER_DEVICE
    PRESENCE -->|"temporarily describes"| USER_DEVICE

    ACCOUNT -.->|"never contains project contents"| OBJECTS
    PROJECT_META -.->|"does not store project files"| PROJECT_FILES
    BILLING -.->|"does not own project data"| AUDIO

    end
    style BACKGROUND fill:#ffffff,stroke:#ffffff,stroke-width:1px
```

### Identity and security

Account identity, device keys, authorization, and encrypted peer traffic.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% Identity and Security Architecture
flowchart TB

    subgraph BACKGROUND

    USER["User"]

    subgraph CLOUD["Cloud Identity"]
        AUTH["Authentication Service"]
        TOKEN["Access Token Service"]
        ACCOUNT["Account Identity"]
        AUTHZ["Authorization / Permission Service"]
    end

    subgraph DEVICE_A["User Device A"]
        DEVICE_ID_A["Device Identity Keypair"]
        KEYSTORE_A["OS-Protected Key Store"]
        RUST_A["Rust Core"]
    end

    subgraph DEVICE_B["User Device B"]
        DEVICE_ID_B["Device Identity Keypair"]
        KEYSTORE_B["OS-Protected Key Store"]
        RUST_B["Rust Core"]
    end

    USER -->|"authenticates"| AUTH
    AUTH -->|"creates authenticated session"| TOKEN
    AUTH -->|"loads account identity"| ACCOUNT

    TOKEN -->|"issues access token to client"| RUST_A
    TOKEN -->|"issues access token to client"| RUST_B

    RUST_A -->|"presents token with API requests"| AUTHZ
    RUST_B -->|"presents token with API requests"| AUTHZ

    AUTHZ -->|"evaluates project permissions"| ACCOUNT

    DEVICE_ID_A -->|"stored securely by"| KEYSTORE_A
    DEVICE_ID_B -->|"stored securely by"| KEYSTORE_B

    RUST_A -->|"uses device identity"| DEVICE_ID_A
    RUST_B -->|"uses device identity"| DEVICE_ID_B

    RUST_A <-->|"mutually authenticates peer"| RUST_B

    RUST_A -->|"encrypts P2P payloads"| RUST_B

    CLOUD -.->|"coordinates identity without possessing private keys"| DEVICE_ID_A
    CLOUD -.->|"coordinates identity without possessing private keys"| DEVICE_ID_B

    end
    style BACKGROUND fill:#ffffff,stroke:#ffffff,stroke-width:1px
```

### Desktop application boundaries

Angular, JUCE, the C-compatible API, and Rust boundaries inside the desktop client.

```mermaid
%%{init: {"theme":"base","themeVariables":{"background":"#ffffff","primaryColor":"#93c5fd","primaryTextColor":"#1e3a5f","primaryBorderColor":"#60a5fa","lineColor":"#5b7c99","secondaryColor":"#93c5fd","tertiaryColor":"#ffffff","clusterBkg":"#bfdbfe","clusterBorder":"#60a5fa","titleColor":"#1e3a5f","fontFamily":" sans-serif"}}}%%
%% Desktop Application — Rust / C++ / Angular Boundaries
flowchart TB

    subgraph BACKGROUND

    subgraph DESKTOP["Cross-Platform Desktop Application"]
        direction TB

        subgraph PRESENTATION["Presentation Layer"]
            ANGULAR["Angular UI"]
        end

        subgraph NATIVE["Native Integration Layer"]
            JUCE["C++ / JUCE Application Shell"]
            DAW_PLUGIN["DAW Plugin / DAW Integration"]
            FILE_UI["Native File System Integration"]
            OS["OS Integration\nWindows / macOS / Linux"]
        end

        subgraph CORE["Rust Core"]
            API["C-Compatible Core API"]
            REPO["Repository Engine"]
            VERSION["Versioning Engine"]
            SYNC["Synchronization Engine"]
            NETWORK["P2P Networking"]
            CRYPTO["Cryptography"]
            STORAGE["Object Storage"]
        end
    end

    ANGULAR -->|"renders application state"| JUCE
    ANGULAR -->|"requests user operations"| JUCE

    JUCE -->|"calls stable native API"| API

    DAW_PLUGIN -->|"requests project operations"| API
    FILE_UI -->|"provides filesystem operations"| API
    OS -->|"provides platform capabilities"| JUCE

    API -->|"controls"| REPO
    API -->|"controls"| VERSION
    API -->|"controls"| SYNC

    REPO -->|"uses"| STORAGE
    VERSION -->|"uses"| STORAGE
    SYNC -->|"uses"| NETWORK
    SYNC -->|"uses"| CRYPTO
    NETWORK -->|"uses"| CRYPTO

    end
    style BACKGROUND fill:#ffffff,stroke:#ffffff,stroke-width:1px
```

# Design Overview

ModelDock is a **management layer** that sits above local model runtimes. It does not run inference itself; it orchestrates discovery, download, caching, installation verification, and loading through pluggable runtime adapters.

---

## Layered View

Dependencies point inward — Clean Architecture with SOLID principles:

```mermaid
graph TB
    subgraph Interface["Interface / Delivery Layer"]
        SDK["Python SDK<br/>modeldock/__init__.py"]
        CLI["CLI<br/>modeldock/cli → Typer"]
    end

    subgraph Application["Application / Use-Case Layer"]
        CORE["modeldock/core/<br/>ModelManager · LifecycleOrchestrator<br/>RegistryService · DownloadService<br/>CacheService · ConfigService"]
    end

    subgraph Domain["Domain Layer — pure, no I/O"]
        DOMAIN["modeldock/domain/<br/>Model · ModelSpec · ModelAlias<br/>Capability · Category<br/>RuntimeBackend · Exceptions"]
    end

    subgraph Ports["Port / Abstraction Layer"]
        PORTS["modeldock/ports/<br/>RuntimePort · RegistryPort<br/>DownloaderPort · CachePort<br/>ProgressPort · EventPort"]
    end

    subgraph Adapters["Adapter / Infrastructure Layer"]
        RUNTIMES["runtimes/<br/>ollama · lmstudio<br/>llamacpp · jan · gpt4all · vllm"]
        REGISTRY["registry/<br/>dynamic catalog + bundled fallback"]
        DOWNLOADERS["downloaders/<br/>http · ollama-native pull"]
        CACHE["cache/<br/>filesystem cache"]
        PROGRESS["progress/<br/>rich · tqdm · silent"]
    end

    subgraph Common["Cross-cutting"]
        COMMON["modeldock/common/<br/>config · logging · errors<br/>platform utils · http client"]
    end

    SDK --> CORE
    CLI --> CORE
    CORE --> PORTS
    CORE --> DOMAIN
    PORTS --> RUNTIMES
    PORTS --> REGISTRY
    PORTS --> DOWNLOADERS
    PORTS --> CACHE
    PORTS --> PROGRESS
    COMMON -.-> CORE
    COMMON -.-> ADAPTERS

    style Interface fill:#37474f,stroke:#26a69a,color:#fff
    style Application fill:#455a64,stroke:#26a69a,color:#fff
    style Domain fill:#546e7a,stroke:#26a69a,color:#fff
    style Ports fill:#607d8b,stroke:#26a69a,color:#fff
    style Adapters fill:#78909c,stroke:#26a69a,color:#fff
    style Common fill:#90a4ae,stroke:#26a69a,color:#fff
```

---

## Key Principle

Domain and ports know nothing about Ollama, HTTP, or the filesystem. The application layer depends only on port *interfaces*. Concrete runtimes/downloaders are injected (Dependency Inversion).

This is what makes adding LM Studio, vLLM, etc. a matter of writing one new adapter class — no changes to core logic.

---

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `domain/` | Pure entities (no I/O, no framework). `Model`, `ModelSpec`, `Capability`, `Category`, `ModelRef`, alias rules. |
| `ports/` | `typing.Protocol` interfaces defining what the system needs from the outside world. |
| `core/` | Application services implementing use cases by composing ports. |
| `adapters/runtimes/` | Concrete runtime integrations implementing `RuntimePort`. |
| `adapters/registry/` | Searchable model catalog. Dynamic from ollama.com with bundled fallback. |
| `adapters/downloaders/` | Moves bytes. Ollama native pull or generic HTTP. |
| `adapters/cache/` | Tracks installed/downloaded artifacts. Filesystem manifest + content hashing. |
| `adapters/progress/` | Pluggable progress reporters (rich, tqdm, silent). |
| `cli/` | Thin delivery layer. Translates argv → core service calls. |
| `common/` | Config, logging, platform helpers, shared HTTP client, base errors. |

---

## Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| Clean Architecture + ports | Maximum extensibility for 6 future runtimes | More files/abstraction upfront |
| Return runtime-native client | Stay lightweight; don't reimplement inference | Less uniform cross-runtime API |
| Dynamic catalog via HTML scraping | Always up-to-date with ollama.com | Depends on ollama.com HTML structure |
| Entry-point plugins | Third parties extend without forking | Slightly more discovery code |
| `httpx` over `requests` | Streaming/resumable downloads, async-ready | Extra dep (small, well-maintained) |
| Optional runtime SDK extras | Tiny base install | User may need `pip install modeldock[ollama]` |

---

## Next Steps

- [Clean Architecture](clean-architecture.md) — dependency rules
- [Runtime Adapters](runtime-adapters.md) — extension points
- [Port Interfaces](ports.md) — the contract
- [Error Handling](errors.md) — typed errors

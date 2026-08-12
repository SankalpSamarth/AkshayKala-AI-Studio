# v5 Master Pipeline Architecture

Below is the complete visual representation of how the `v5_Earring_Mockup_Final` system is wired together. 

Because GitHub automatically supports Mermaid diagrams, this code block will render as a beautiful, interactive flowchart (exactly like Freeform) when you look at it on your GitHub repository!

```mermaid
graph LR
    %% Styling
    classDef client fill:#f59e0b,stroke:#fff,stroke-width:2px,color:#fff;
    classDef app fill:#1E40AF,stroke:#fff,stroke-width:2px,color:#fff;
    classDef data fill:#b91c1c,stroke:#fff,stroke-width:2px,color:#fff;
    classDef cloud fill:#a21caf,stroke:#fff,stroke-width:2px,color:#fff;

    %% Client Tier
    Client([User Web Browser]):::client

    %% Application Tier (Docker)
    subgraph AppServer [Application Tier: Docker Container]
        direction TB
        Gradio[Gradio Web Server: Port 7860]:::app
        Core[Python Processing Engine]:::app
        CV[Computer Vision Module: ISNet]:::app
        
        Gradio --- Core
        Core --- CV
    end

    %% Data Storage Tier
    subgraph DataTier [Local Storage Tier]
        direction TB
        JSON[(api_keys.json Database)]:::data
        ENV[.env Configuration]:::data
    end

    %% External Services Tier
    subgraph ExternalServices [External Cloud APIs]
        direction TB
        Claid((Claid.ai Fashion API)):::cloud
        Uguu((Uguu.se Object Storage)):::cloud
    end

    %% Connections showing data flow between tiers
    Client <-->|HTTP/WS| Gradio
    Core <-->|File I/O| JSON
    Core <-->|File I/O| ENV
    Core <-->|REST API over HTTPS| Claid
    Core <-->|REST API over HTTPS| Uguu
```

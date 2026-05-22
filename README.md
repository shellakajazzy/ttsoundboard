[![Entangled badge](https://img.shields.io/badge/entangled-Use%20the%20source!-%2300aeff)](https://entangled.github.io/)

# TTSoundboard
My TTS and soundboard solution.

It uses a server at the core that accepts HTTP API calls and clients will connect to through a TCP socket that will stream the generated TTS or soundboard audio realtime.
Although this means that any client can make an API call to the server, I am only planning it to use on my private Tailscale meshnet VPN.
I may or may not make the server require an API key to respond to requests to further address this, but for the scope of this project I doubt I will have to until I have implemented the features I want.

In this repo, I have provided an example Discord client for both making API calls and playing back the generated audio in a VC.

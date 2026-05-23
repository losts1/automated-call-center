# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of AI legal call center
- LiveKit + Twilio SIP trunk integration
- ElevenLabs voice (STT/TTS) integration
- Local LLM (Ollama/lawllm) for conversation intelligence
- AWS moto mocks for state management and recording storage
- Twilio webhook handler with CORS and health checks

### Changed
- Replaced hardcoded credentials with environment variables
- Added proper logging across all modules
- Added CORS middleware to webhook endpoints

### Fixed
- TwiML SIP URL syntax error (missing `>` after `sip:`)
- Git history cleaned of hardcoded secrets

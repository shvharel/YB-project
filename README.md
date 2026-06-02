# CommonTalks – Encrypted Social Network & Media Streaming Platform

A full-stack Python social networking application with end-to-end encrypted 
messaging, voice, and video calls.

## Features

### User System
- Registration with profile picture upload and hobby selection
- Login with secure authentication
- User discovery sorted by number of shared hobbies

### Messaging
- Real-time chat between matched users
- All messages saved to DB in encrypted form – server stores ciphertext only
- End-to-end encrypted: server never sees plaintext

### Voice & Video Calls
- Live VoIP voice calls over UDP
- Video calls over UDP on separate packet stream
- All call data E2EE – server forwards encrypted packets only

## Security Architecture
- Diffie-Hellman key exchange initiated on invite acceptance
- Each user pair generates a unique shared secret
- AES-256 encrypts all communication between the pair
- Server stores and forwards ciphertext only – zero plaintext exposure
- Key exchange flow:
  1. User A invites User B
  2. Public keys exchanged (or retrieved from DB)
  3. Both sides derive shared secret independently
  4. All further communication encrypted with that secret

## Tech Stack
- Language: Python
- GUI: PySide6
- Database: SQLite (stores encrypted messages and user data)
- Encryption: DH + AES-256 (E2EE)
- Networking: TCP (messaging/signaling) + UDP (voice/video)

# Flight Booking Chatbot

A rule-based Natural Language Processing (NLP) chatbot that assists users with booking flights through natural language conversation — built using classical NLP techniques rather than large language models or external APIs.

## Overview

The chatbot supports flight search, one-way and return bookings, booking modification and cancellation, and simple conversational interactions (greetings, small talk), all through a fully transparent, explainable pipeline: TF-IDF vectorisation, cosine similarity, regular expressions, and a rule-based dialogue manager.

The system follows a modular architecture so each component has a single, clearly defined responsibility — making the chatbot easy to debug, extend, and reason about.

## Architecture

The chatbot processes every message through a seven-stage pipeline:

1. **User Input**
2. **Text Preprocessing**
3. **Intent Recognition**
4. **Slot Filling**
5. **Dialogue Manager**
6. **Flight Search Engine**
7. **Natural Language Generation**

Each stage performs one task before passing its output to the next.

### 1. Text Preprocessing

Cleans and normalises every message before classification: lowercasing, punctuation removal, whitespace normalisation, contraction standardisation, and date normalisation. Without this step, `"Book Flight"`, `"book flight"`, and `"BOOK FLIGHT"` would be treated as different inputs — preprocessing ensures similar sentences produce similar TF-IDF vectors, which directly improves classification accuracy.

### 2. Intent Recognition

Determines *what* the user wants (`greeting`, `book_flight`, `modify_booking`, `cancel_booking`, `help`, `small_talk`, `unknown`, etc.) using a TF-IDF + cosine similarity classifier trained on labelled example utterances (`intents.json`):

1. Training utterances are vectorised with TF-IDF.
2. A centroid vector is computed for each intent.
3. New input is vectorised and compared against every centroid via cosine similarity.
4. The closest intent is returned — unless the best score falls below a confidence threshold, in which case the chatbot returns `unknown` rather than guessing.

Chosen over a deep learning approach for being fast, explainable, lightweight, and fully offline.

### 3. Slot Filling

Extracts the *details* behind an intent — origin, destination, departure date, return date, passenger count, cabin class, trip type — using regular expressions, keyword matching, and context-aware updates. For example, `"Book me a flight from London to Rome tomorrow"` extracts origin, destination, and date in a single pass. Extracted slots are stored in the `DialogueState`.

### 4. Dialogue State

Maintains conversation state across turns (name, booking status, all slot values, confirmation state, selected flight), enabling multi-turn conversations without the user repeating themselves. E.g. `"Change my cabin to Business"` updates only the cabin while retaining origin, destination, date, and passenger count already collected.

### 5. Dialogue Manager

The central controller, responsible for:

- **Intent routing** — deciding which action to take (booking, modification, cancellation, help, small talk) based on the predicted intent.
- **Slot prompting** — asking targeted follow-up questions for missing information (e.g. *"Would that be a return trip or a single flight?"*) instead of restarting the flow.
- **Conversation flow** — enforcing a logical order: greeting → booking → collect details → search → show results → confirm → complete.
- **Booking confirmation** — presenting a full summary (origin, destination, dates, passengers, cabin, price) and requiring explicit user confirmation before saving.
- **Modify / cancel booking** — supports changing any slot without restarting, and requires confirmation before deleting a booking.
- **Unknown intent handling** — responds with a clarification request rather than guessing when confidence is too low.

### 6. Flight Search Engine

Reads flight data from `flights.csv` into `FlightOption` objects (origin, destination, date, carrier, cabin, price, departure time).

- **Exact search** — matches origin, destination, date, and cabin exactly, sorted by price.
- **Similar search** — if no exact match exists, relaxes date/cabin while keeping origin and destination fixed, returning the best three alternatives to avoid dead ends.
- **Return trip search** — searches outbound and inbound legs independently and returns the cheapest valid combinations.

### 7. Natural Language Generation

Converts structured results into conversational responses via consistent, maintainable templates rather than printing raw data — e.g. a full itinerary summary with route, date, cabin, passengers, and price.

## Additional Features

- **Greeting & memory** — recognises greetings, introduces itself, asks for and remembers the user's name (*"Nice to see you again Chidi."*)
- **Help intent** — explains supported functionality on request
- **Small talk** — handles conversational asides (*"How are you?"*) without derailing the booking flow
- **Booking summaries** — generates a readable itinerary before every confirmation

## Conversational Design Principles

- **Turn-taking** — one focused question at a time
- **Progressive slot-filling** — information collected incrementally, not all at once
- **Grounding** — key details confirmed via summary before booking
- **Repair strategies** — unclear input triggers clarification, not incorrect assumptions
- **User agency** — explicit confirmation required for bookings and cancellations
- **Context retention** — prior information remembered across turns
- **Consistency** — predictable, template-based responses
- **Restricted domain** — politely declines out-of-scope requests rather than attempting them

## Evaluation

**Performance:**
- Intent classification accuracy measured against a labelled test set
- Scenario-based dialogue testing covering one-way/return bookings, modification, cancellation, and error handling
- Response time measured with Python's `time.perf_counter()`: average of **0.48ms** per interaction across a full conversation (individual messages ranging 0.6–0.7ms)

**Usability:**
- Assessed with the **Chatbot Usability Questionnaire (CUQ)** across ease of use, personality, navigation, error handling, response quality, and overall usability, producing a quantitative usability score.

## Summary

A modular, rule-based conversational agent combining classical NLP (TF-IDF intent recognition, regex-based slot extraction) with structured dialogue management to deliver a transparent, explainable, and computationally efficient flight-booking experience — demonstrating that traditional NLP methods remain a strong fit for well-defined, restricted-domain conversational systems, without dependence on large language models.

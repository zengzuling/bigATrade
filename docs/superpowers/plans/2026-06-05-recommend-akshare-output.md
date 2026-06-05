# Recommend AkShare Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `python -m bigatrade recommend --date YYYY-MM-DD --top N` produce a real CSV recommendation file from stock list and daily bars supplied by an AkShare-backed provider.

**Architecture:** Keep AkShare behind a small provider interface so tests can use in-memory fake data. The recommendation service composes existing indicator, scoring, and trade-plan modules, then the output layer writes deterministic CSV rows.

**Tech Stack:** Python, pandas, Typer, pytest, AkShare.

---

## Task 1: Data Provider Interface

Create `src/bigatrade/data/models.py` with `StockInfo`, and `src/bigatrade/data/akshare_provider.py` with `AkShareProvider`.

TDD target: provider normalizes AkShare-style Chinese columns into internal English columns.

## Task 2: Recommend Service

Create `src/bigatrade/recommend/service.py`.

TDD target: fake provider with one strong and one ST stock returns only the strong stock trade plan.

## Task 3: CSV Writer

Create `src/bigatrade/output/writers.py`.

TDD target: trade plans are written to CSV with stable Chinese headers and reason/risk text joined by semicolon.

## Task 4: CLI Wiring

Modify `src/bigatrade/cli.py`.

TDD target: CLI can run recommend with a fake service and prints the output CSV path. Runtime CLI uses `AkShareProvider`.

## Task 5: Verification

Run `python -m pytest -q`, then run `python -m bigatrade recommend --help` to verify the command surface.

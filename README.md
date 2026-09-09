# Backend Engineering PoCs & Advanced Patterns

A collection of Proof of Concepts (PoCs) built with Django and PostgreSQL to explore, benchmark, and solve advanced backend engineering challenges. This repository serves as an interactive laboratory for system design concepts, performance optimization, and scalable architecture.

## Tech Stack
* **Core:** Python, Django
* **Databases:** PostgreSQL (Essential for row-level locking and advanced data integrity features)
* **Upcoming Integrations:** Redis, Celery, RabbitMQ, Docker, Elasticsearch

---

## Laboratory Modules

### 1. Concurrency & Database Locks (`concurrency_locks/`)
**Objective:** Handle high-traffic concurrent requests safely without data corruption or lost updates.

**The Scenario:** A Flash Sale endpoint where 100+ concurrent threads attempt to purchase the last available item at the exact same millisecond.

**The Problem (Race Condition & Lost Updates):**
A naive `stock -= 1` operation without database-level synchronization results in a "Lost Update" anomaly. Multiple requests read `stock = 1` into memory simultaneously, pass the `stock > 0` validation, and overwrite each other. The system falsely reports multiple successful purchases for a single item.

**Implemented Solutions & Trade-offs:**

*   **Approach A: Pessimistic Locking (`select_for_update`)**
    *   *Mechanism:* Locks the database row until the current transaction completes. Concurrent requests wait in a queue.
    *   *Pros:* Absolute data integrity. Simple to implement.
    *   *Cons:* Can lead to database bottlenecks, connection pool exhaustion, and timeouts under extreme load.
    *   *Implementation:* Wrapped in `transaction.atomic()` utilizing Django's `select_for_update()`.

*   **Approach B: Optimistic Locking (Versioning)**
    *   *Mechanism:* Introduces a `version` field. The update only succeeds if the version matches the initially read state. Uses `F()` expressions to delegate atomic calculations to the database engine.
    *   *Pros:* Exceptionally fast, no database queuing, highly scalable for read-heavy/write-heavy mixed loads.
    *   *Cons:* Requires application-level logic to handle conflicts.
    *   *Implementation:* Conditional `.update()` query combined with a `while` loop (retry mechanism) to seamlessly re-attempt the purchase behind the scenes without failing the user request.

---

### 2. Performance, Caching & Asynchronous Processing (`caching_performance/`)
**Objective:** Architect a highly scalable, Read-Heavy & Write-Heavy system capable of handling thousands of concurrent requests with sub-10ms latency.

**The Scenario:** A URL Shortener tracking clicks in real-time. 
*   **The Problem:** Updating the database synchronously on every click (`clicks += 1`) causes severe database locking, high latency (~248ms), and a massive error rate (~48% under heavy load) due to disk I/O bottlenecks and race conditions.

**Implemented Solutions & Architectural Patterns:**

*   **Read-Through Cache:** 
    *   Cached the `original_url` in Redis. Reduced read latency from ~178ms to ~2ms and eliminated database read bottlenecks.
*   **Write-Behind (Write-Back) Caching Strategy:**
    *   Instead of writing to PostgreSQL on every click, clicks are tracked entirely in Redis memory using atomic operations, maintaining zero-latency writes.
*   **Atomic Lua Scripts:**
    *   Implemented custom Redis Lua scripts to handle incrementing, delta extraction, and fault-recovery operations atomically, preventing race conditions *inside* Redis itself.
*   **Asynchronous Synchronization (Celery & RabbitMQ/Redis):**
    *   **Smart Polling:** Utilized Redis Sets (`SADD`, `SMEMBERS`) to track only active URLs, avoiding full database scans.
    *   **Delta Sync:** A Celery Beat dispatcher checks active URLs. When a URL hits a threshold (e.g., 50 clicks), a background Celery worker extracts the delta and updates PostgreSQL in the background.
    *   **Fault Tolerance & Exponential Backoff:** If the PostgreSQL transaction fails (e.g., DB is down), a Lua script restores the un-synced clicks back to Redis, and the Celery worker retries using exponential backoff, ensuring zero data loss.

**📈 Benchmark Results (Apache Benchmark / JMeter):**
*Test conditions: 100 concurrent requests testing the read & write-back endpoints.*

| Metric | Naive Approach (PostgreSQL Only) | Optimized (Redis + Celery) | Impact / Improvement |
| :--- | :--- | :--- | :--- |
| **Average Response Time** | 128 ms | **32 ms** (Min: 5 ms) | **~4x Faster** |
| **Throughput (req/sec)** | 88.3 req/sec | **100.9 req/sec** | Improved (Scales seamlessly under heavier loads) |
| **Error Rate** | High under heavy load (Locks) | **0.00%** | Complete elimination of DB Race Conditions |
| **Database I/O** | 1 Read + 1 Write per click | **Zero** synchronous DB hits | Database breathes; writes are batched in background |

---
---

## Local Setup & Benchmarking

```bash
# 1. Clone the repository
git clone [https://github.com/yourusername/backend-engineering-pocs.git](https://github.com/yourusername/backend-engineering-pocs.git)
cd backend-engineering-pocs

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure PostgreSQL credentials in settings.py, then migrate
python manage.py migrate

# 5. Run the server
python manage.py runserver
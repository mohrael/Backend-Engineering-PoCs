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

### 2. Performance & In-Memory Caching 
**Objective:** Optimizing high-read architectures and mitigating database bottlenecks.
**Concepts:** N+1 Query resolution, B-Tree Indexing optimizations, Redis In-Memory Caching, and Cache Stampede mitigation.

### 3. Asynchronous Processing 
**Objective:** Offloading heavy I/O bound tasks to background workers to ensure instant API responses.
**Concepts:** Message Brokers (RabbitMQ), Distributed Task Queues (Celery), and Event-driven triggers.

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
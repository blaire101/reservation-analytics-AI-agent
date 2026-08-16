# Code Walkthrough

## The four files to understand first

```text
app/core/graph.py
app/core/extractor.py
app/analytics/resolver.py
app/analytics/service.py
```

### `graph.py`
Owns workflow only:

```text
extract -> knowledge
       or
extract -> validate -> resolve -> analytics
```

It also checks whether the same `session_id` is waiting for clarification.

### `extractor.py`
Owns language understanding only:

```text
question -> intent + metric + ReservationQuery
```

It does not decide warehouse IDs.

### `resolver.py`
Owns business-context orchestration only:

```text
country if supplied
-> product if supplied
-> campaign
-> final stable IDs
```

Candidate SQL is in `repository.py`. Matching logic is in `selector.py`.

### `service.py`
Owns controlled analytics only:

```text
resolved Campaign
-> predefined aggregate/detail SQL
-> formatted answer
```

## Why product is optional

A campaign row already contains `fproduct_id` and `fcountry_code`.

Therefore this request is valid:

```text
Germany + campaign name + reserved_users
```

The resolver can find the campaign and then derive the product from that governed row.

Product is still useful when the user supplies it because it narrows the campaign candidate set.

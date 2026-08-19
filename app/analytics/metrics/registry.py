"""Central allowlist of business metrics that controlled analytics may run."""

# The LLM may select only one of these metric names through structured output.
# Application code, not the LLM, decides which SQL corresponds to each metric.
ALLOWED_METRICS = {
    'summary',
    'reserved_users',
    'ordered_users',
    'reserved_not_ordered',
    'conversion_rate',
}

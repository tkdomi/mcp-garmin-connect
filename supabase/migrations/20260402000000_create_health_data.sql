CREATE TABLE IF NOT EXISTS health_data (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  data_type     TEXT NOT NULL,
  recorded_date DATE NOT NULL,
  raw_data      JSONB NOT NULL,
  synced_at     TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(data_type, recorded_date)
);

CREATE INDEX IF NOT EXISTS idx_health_date ON health_data(data_type, recorded_date DESC);

-- Migration 008: Campaign Memories
-- Persistent narrative memory for campaigns. SAM auto-extracts facts after each response.

CREATE TABLE IF NOT EXISTS campaign_memories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id uuid REFERENCES campaigns(id) ON DELETE CASCADE NOT NULL,
  content text NOT NULL,
  type text DEFAULT 'fact' CHECK (type IN ('fact', 'npc', 'location', 'plot', 'item', 'decision')),
  importance integer DEFAULT 5 CHECK (importance BETWEEN 1 AND 10),
  session_number integer,
  embedding vector(768),
  created_at timestamptz DEFAULT now(),
  created_by uuid REFERENCES profiles(id),
  source text DEFAULT 'auto' CHECK (source IN ('manual', 'auto', 'session_summary'))
);

CREATE INDEX idx_campaign_memories_campaign ON campaign_memories(campaign_id, importance DESC);
CREATE INDEX idx_campaign_memories_type ON campaign_memories(campaign_id, type);

-- RLS
ALTER TABLE campaign_memories ENABLE ROW LEVEL SECURITY;

-- Players in the campaign can read memories
CREATE POLICY "Players can view campaign memories" ON campaign_memories
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM characters
      WHERE characters.campaign_id = campaign_memories.campaign_id
      AND characters.user_id = auth.uid()
    )
    OR
    EXISTS (
      SELECT 1 FROM campaigns
      WHERE campaigns.id = campaign_memories.campaign_id
      AND campaigns.gm_id = auth.uid()
    )
  );

-- Only GM (campaign owner) or service role can insert/update/delete
CREATE POLICY "GM can manage campaign memories" ON campaign_memories
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM campaigns
      WHERE campaigns.id = campaign_memories.campaign_id
      AND campaigns.gm_id = auth.uid()
    )
  );

COMMENT ON TABLE campaign_memories IS 'Persistent narrative facts extracted by SAM or added by GM. Injected into campaign_context for long-term memory.';

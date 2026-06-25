-- Drop existing policies and recreate for public access
DROP POLICY IF EXISTS select_complaints ON complaints;
DROP POLICY IF EXISTS select_incidents ON incidents;
DROP POLICY IF EXISTS select_incident_complaints ON incident_complaints;

-- Create new policies that allow anon access (for read operations)
CREATE POLICY "select_complaints" ON complaints FOR SELECT
  TO anon, authenticated USING (true);

CREATE POLICY "select_incidents" ON incidents FOR SELECT
  TO anon, authenticated USING (true);

CREATE POLICY "select_incident_complaints" ON incident_complaints FOR SELECT
  TO anon, authenticated USING (true);

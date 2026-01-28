-- Ad Platform MVP - RLS Policies & Helper Functions
-- Version: 1.0.0
-- Date: 2024-01-28

-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE connected_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE ad_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE hourly_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommended_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_digests ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_rate_limits ENABLE ROW LEVEL SECURITY;

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get user's organization ID
CREATE OR REPLACE FUNCTION get_user_org_id()
RETURNS UUID AS $$
BEGIN
    RETURN (SELECT org_id FROM users WHERE id = auth.uid());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Check if user is org owner/admin
CREATE OR REPLACE FUNCTION is_org_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN (
        SELECT role IN ('owner', 'admin') 
        FROM users 
        WHERE id = auth.uid()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- ORGANIZATIONS POLICIES
-- ============================================
CREATE POLICY "Users can view their organization"
    ON organizations FOR SELECT
    USING (id = get_user_org_id());

CREATE POLICY "Admins can update their organization"
    ON organizations FOR UPDATE
    USING (id = get_user_org_id() AND is_org_admin());

-- ============================================
-- USERS POLICIES
-- ============================================
CREATE POLICY "Users can view members of their organization"
    ON users FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Users can update their own profile"
    ON users FOR UPDATE
    USING (id = auth.uid());

CREATE POLICY "Admins can manage org users"
    ON users FOR ALL
    USING (org_id = get_user_org_id() AND is_org_admin());

-- ============================================
-- CONNECTED ACCOUNTS POLICIES
-- ============================================
CREATE POLICY "Users can view their org's connected accounts"
    ON connected_accounts FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Admins can manage connected accounts"
    ON connected_accounts FOR ALL
    USING (org_id = get_user_org_id() AND is_org_admin());

-- ============================================
-- CAMPAIGNS POLICIES
-- ============================================
CREATE POLICY "Users can view campaigns of their org's accounts"
    ON campaigns FOR SELECT
    USING (
        account_id IN (
            SELECT id FROM connected_accounts 
            WHERE org_id = get_user_org_id()
        )
    );

-- ============================================
-- AD SETS POLICIES
-- ============================================
CREATE POLICY "Users can view ad sets of their org's accounts"
    ON ad_sets FOR SELECT
    USING (
        account_id IN (
            SELECT id FROM connected_accounts 
            WHERE org_id = get_user_org_id()
        )
    );

-- ============================================
-- DAILY METRICS POLICIES
-- ============================================
CREATE POLICY "Users can view metrics of their org's accounts"
    ON daily_metrics FOR SELECT
    USING (
        account_id IN (
            SELECT id FROM connected_accounts 
            WHERE org_id = get_user_org_id()
        )
    );

-- ============================================
-- HOURLY METRICS POLICIES
-- ============================================
CREATE POLICY "Users can view hourly metrics of their org's accounts"
    ON hourly_metrics FOR SELECT
    USING (
        account_id IN (
            SELECT id FROM connected_accounts 
            WHERE org_id = get_user_org_id()
        )
    );

-- ============================================
-- INSIGHTS POLICIES
-- ============================================
CREATE POLICY "Users can view their org's insights"
    ON insights FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Users can update insight read status"
    ON insights FOR UPDATE
    USING (org_id = get_user_org_id())
    WITH CHECK (org_id = get_user_org_id());

-- ============================================
-- RECOMMENDED ACTIONS POLICIES
-- ============================================
CREATE POLICY "Users can view their org's recommended actions"
    ON recommended_actions FOR SELECT
    USING (org_id = get_user_org_id());

CREATE POLICY "Admins can update action status"
    ON recommended_actions FOR UPDATE
    USING (org_id = get_user_org_id() AND is_org_admin());

-- ============================================
-- DAILY DIGESTS POLICIES
-- ============================================
CREATE POLICY "Users can view their org's digests"
    ON daily_digests FOR SELECT
    USING (org_id = get_user_org_id());

-- ============================================
-- SYNC JOBS POLICIES
-- ============================================
CREATE POLICY "Users can view sync jobs of their org's accounts"
    ON sync_jobs FOR SELECT
    USING (
        account_id IN (
            SELECT id FROM connected_accounts 
            WHERE org_id = get_user_org_id()
        )
    );

-- ============================================
-- API RATE LIMITS POLICIES (Admin only)
-- ============================================
CREATE POLICY "Admins can view rate limits"
    ON api_rate_limits FOR SELECT
    USING (
        account_id IN (
            SELECT id FROM connected_accounts 
            WHERE org_id = get_user_org_id()
        ) AND is_org_admin()
    );

-- ============================================
-- SERVICE ROLE BYPASS
-- (Backend uses service_role key which bypasses RLS)
-- ============================================

-- ============================================
-- HELPER FUNCTIONS FOR METRICS
-- ============================================

-- Calculate CTR
CREATE OR REPLACE FUNCTION calculate_ctr(impressions BIGINT, clicks BIGINT)
RETURNS DECIMAL(10, 6) AS $$
BEGIN
    IF impressions = 0 OR impressions IS NULL THEN
        RETURN 0;
    END IF;
    RETURN (clicks::DECIMAL / impressions::DECIMAL);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate CPC (in micros)
CREATE OR REPLACE FUNCTION calculate_cpc(spend_micros BIGINT, clicks BIGINT)
RETURNS BIGINT AS $$
BEGIN
    IF clicks = 0 OR clicks IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN (spend_micros / clicks);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate CPM (in micros)
CREATE OR REPLACE FUNCTION calculate_cpm(spend_micros BIGINT, impressions BIGINT)
RETURNS BIGINT AS $$
BEGIN
    IF impressions = 0 OR impressions IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN (spend_micros * 1000 / impressions);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate ROAS
CREATE OR REPLACE FUNCTION calculate_roas(conversion_value_micros BIGINT, spend_micros BIGINT)
RETURNS DECIMAL(10, 4) AS $$
BEGIN
    IF spend_micros = 0 OR spend_micros IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN (conversion_value_micros::DECIMAL / spend_micros::DECIMAL);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Calculate CPA (in micros)
CREATE OR REPLACE FUNCTION calculate_cpa(spend_micros BIGINT, conversions DECIMAL)
RETURNS BIGINT AS $$
BEGIN
    IF conversions = 0 OR conversions IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN (spend_micros / conversions)::BIGINT;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- AGGREGATE METRICS VIEW
-- ============================================
CREATE OR REPLACE VIEW v_account_metrics_summary AS
SELECT 
    ca.id AS account_id,
    ca.org_id,
    ca.platform,
    ca.platform_account_name,
    dm.date,
    SUM(dm.impressions) AS total_impressions,
    SUM(dm.clicks) AS total_clicks,
    SUM(dm.spend_micros) AS total_spend_micros,
    SUM(dm.conversions) AS total_conversions,
    SUM(dm.conversion_value_micros) AS total_conversion_value_micros,
    calculate_ctr(SUM(dm.impressions), SUM(dm.clicks)) AS overall_ctr,
    calculate_cpc(SUM(dm.spend_micros), SUM(dm.clicks)) AS overall_cpc_micros,
    calculate_roas(SUM(dm.conversion_value_micros), SUM(dm.spend_micros)) AS overall_roas
FROM connected_accounts ca
LEFT JOIN daily_metrics dm ON ca.id = dm.account_id
WHERE ca.is_active = TRUE
GROUP BY ca.id, ca.org_id, ca.platform, ca.platform_account_name, dm.date;

-- ============================================
-- ORGANIZATION METRICS SUMMARY VIEW
-- ============================================
CREATE OR REPLACE VIEW v_org_metrics_summary AS
SELECT 
    ca.org_id,
    dm.date,
    SUM(dm.impressions) AS total_impressions,
    SUM(dm.clicks) AS total_clicks,
    SUM(dm.spend_micros) AS total_spend_micros,
    SUM(dm.conversions) AS total_conversions,
    SUM(dm.conversion_value_micros) AS total_conversion_value_micros,
    calculate_ctr(SUM(dm.impressions), SUM(dm.clicks)) AS overall_ctr,
    calculate_cpc(SUM(dm.spend_micros), SUM(dm.clicks)) AS overall_cpc_micros,
    calculate_roas(SUM(dm.conversion_value_micros), SUM(dm.spend_micros)) AS overall_roas,
    COUNT(DISTINCT ca.id) AS active_accounts,
    COUNT(DISTINCT c.id) AS active_campaigns
FROM connected_accounts ca
LEFT JOIN daily_metrics dm ON ca.id = dm.account_id
LEFT JOIN campaigns c ON ca.id = c.account_id AND c.is_active = TRUE
WHERE ca.is_active = TRUE
GROUP BY ca.org_id, dm.date;

-- ============================================
-- SEED DATA FOR DEVELOPMENT (Optional)
-- ============================================
-- Uncomment below for development/testing

/*
-- Create a test organization
INSERT INTO organizations (id, name, slug, default_currency, default_timezone)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Test Organization',
    'test-org',
    'TRY',
    'Europe/Istanbul'
);

-- Note: Users should be created through Supabase Auth
-- The trigger will need to be set up in Supabase Dashboard
*/

-- ============================================
-- AUTH TRIGGER FOR NEW USER
-- ============================================
-- This function creates a user profile when someone signs up
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if user already has an org from signup metadata
    IF NEW.raw_user_meta_data->>'org_id' IS NOT NULL THEN
        INSERT INTO users (id, org_id, email, full_name)
        VALUES (
            NEW.id,
            (NEW.raw_user_meta_data->>'org_id')::UUID,
            NEW.email,
            COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1))
        );
    ELSE
        -- Create a new organization for the user
        WITH new_org AS (
            INSERT INTO organizations (name, slug)
            VALUES (
                COALESCE(NEW.raw_user_meta_data->>'org_name', split_part(NEW.email, '@', 1) || '''s Organization'),
                lower(replace(NEW.id::text, '-', ''))
            )
            RETURNING id
        )
        INSERT INTO users (id, org_id, email, full_name, role)
        SELECT 
            NEW.id,
            new_org.id,
            NEW.email,
            COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
            'owner'
        FROM new_org;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users
CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================
-- USEFUL QUERIES FOR DEBUGGING (Run manually)
-- ============================================
/*
-- Check all tables
SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name)))
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;

-- Check RLS policies
SELECT tablename, policyname, cmd, qual
FROM pg_policies
WHERE schemaname = 'public';

-- Check indexes
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
*/

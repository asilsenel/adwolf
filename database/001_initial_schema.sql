-- Ad Platform MVP - Initial Database Schema
-- Version: 1.0.0
-- Date: 2024-01-28

-- ============================================
-- EXTENSIONS
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- ENUMS
-- ============================================
CREATE TYPE platform_type AS ENUM ('google_ads', 'meta_ads', 'amazon_ads', 'tiktok_ads');
CREATE TYPE account_status AS ENUM ('active', 'paused', 'disconnected', 'error');
CREATE TYPE sync_status AS ENUM ('pending', 'running', 'completed', 'failed');
CREATE TYPE insight_type AS ENUM ('performance', 'optimization', 'alert', 'opportunity', 'anomaly');
CREATE TYPE insight_priority AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE action_status AS ENUM ('pending', 'approved', 'executed', 'dismissed', 'failed');
CREATE TYPE digest_channel AS ENUM ('email', 'whatsapp', 'both');

-- ============================================
-- ORGANIZATIONS (Multi-tenant)
-- ============================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    logo_url TEXT,
    settings JSONB DEFAULT '{}',
    default_currency VARCHAR(3) DEFAULT 'TRY',
    default_timezone VARCHAR(50) DEFAULT 'Europe/Istanbul',
    subscription_tier VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- USERS (Linked to Supabase Auth)
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    role VARCHAR(50) DEFAULT 'member', -- owner, admin, member, viewer
    preferences JSONB DEFAULT '{}',
    notification_settings JSONB DEFAULT '{
        "email_daily_digest": true,
        "email_alerts": true,
        "whatsapp_alerts": false,
        "whatsapp_number": null
    }',
    last_seen_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_org ON users(org_id);
CREATE INDEX idx_users_email ON users(email);

-- ============================================
-- CONNECTED ACCOUNTS (OAuth Tokens)
-- ============================================
CREATE TABLE connected_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    connected_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Platform info
    platform platform_type NOT NULL,
    platform_account_id VARCHAR(255) NOT NULL, -- External account ID
    platform_account_name VARCHAR(255),
    
    -- OAuth tokens (encrypted)
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    
    -- Status & metadata
    status account_status DEFAULT 'active',
    last_sync_at TIMESTAMPTZ,
    last_sync_status sync_status,
    last_error TEXT,
    
    -- Platform-specific settings
    settings JSONB DEFAULT '{}',
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(org_id, platform, platform_account_id)
);

CREATE INDEX idx_connected_accounts_org ON connected_accounts(org_id);
CREATE INDEX idx_connected_accounts_platform ON connected_accounts(platform);
CREATE INDEX idx_connected_accounts_status ON connected_accounts(status);

-- ============================================
-- CAMPAIGNS
-- ============================================
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES connected_accounts(id) ON DELETE CASCADE,
    
    -- Platform identifiers
    platform_campaign_id VARCHAR(255) NOT NULL,
    platform platform_type NOT NULL,
    
    -- Campaign info
    name VARCHAR(500) NOT NULL,
    status VARCHAR(50), -- enabled, paused, removed
    campaign_type VARCHAR(100), -- search, display, shopping, video, etc.
    
    -- Budget
    daily_budget_micros BIGINT, -- Amount in micros (divide by 1M for actual)
    budget_currency VARCHAR(3),
    
    -- Bidding
    bidding_strategy VARCHAR(100),
    target_cpa_micros BIGINT,
    target_roas DECIMAL(10, 4),
    
    -- Dates
    start_date DATE,
    end_date DATE,
    
    -- Metadata
    labels JSONB DEFAULT '[]',
    settings JSONB DEFAULT '{}',
    
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(account_id, platform_campaign_id)
);

CREATE INDEX idx_campaigns_account ON campaigns(account_id);
CREATE INDEX idx_campaigns_platform ON campaigns(platform);
CREATE INDEX idx_campaigns_status ON campaigns(status);

-- ============================================
-- AD SETS / AD GROUPS
-- ============================================
CREATE TABLE ad_sets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES connected_accounts(id) ON DELETE CASCADE,
    
    -- Platform identifiers
    platform_ad_set_id VARCHAR(255) NOT NULL,
    platform platform_type NOT NULL,
    
    -- Ad set info
    name VARCHAR(500) NOT NULL,
    status VARCHAR(50),
    
    -- Targeting (simplified)
    targeting_summary JSONB DEFAULT '{}',
    
    -- Budget (if applicable)
    daily_budget_micros BIGINT,
    
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(campaign_id, platform_ad_set_id)
);

CREATE INDEX idx_ad_sets_campaign ON ad_sets(campaign_id);
CREATE INDEX idx_ad_sets_account ON ad_sets(account_id);

-- ============================================
-- DAILY METRICS (Normalized)
-- ============================================
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES connected_accounts(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    ad_set_id UUID REFERENCES ad_sets(id) ON DELETE CASCADE,
    
    platform platform_type NOT NULL,
    date DATE NOT NULL,
    
    -- Core metrics
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    spend_micros BIGINT DEFAULT 0, -- In micros for precision
    currency VARCHAR(3) DEFAULT 'TRY',
    
    -- Conversions
    conversions DECIMAL(18, 4) DEFAULT 0,
    conversion_value_micros BIGINT DEFAULT 0,
    
    -- Calculated metrics (stored for performance)
    ctr DECIMAL(10, 6), -- Click-through rate
    cpc_micros BIGINT, -- Cost per click
    cpm_micros BIGINT, -- Cost per mille
    roas DECIMAL(10, 4), -- Return on ad spend
    cpa_micros BIGINT, -- Cost per acquisition
    
    -- Platform-specific extra metrics
    extra_metrics JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(account_id, campaign_id, ad_set_id, date)
);

CREATE INDEX idx_daily_metrics_account ON daily_metrics(account_id);
CREATE INDEX idx_daily_metrics_campaign ON daily_metrics(campaign_id);
CREATE INDEX idx_daily_metrics_date ON daily_metrics(date);
CREATE INDEX idx_daily_metrics_platform ON daily_metrics(platform);
CREATE INDEX idx_daily_metrics_account_date ON daily_metrics(account_id, date);

-- ============================================
-- HOURLY METRICS (Optional - for real-time)
-- ============================================
CREATE TABLE hourly_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES connected_accounts(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    
    platform platform_type NOT NULL,
    datetime TIMESTAMPTZ NOT NULL,
    
    -- Core metrics
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    spend_micros BIGINT DEFAULT 0,
    conversions DECIMAL(18, 4) DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(account_id, campaign_id, datetime)
);

CREATE INDEX idx_hourly_metrics_account ON hourly_metrics(account_id);
CREATE INDEX idx_hourly_metrics_datetime ON hourly_metrics(datetime);

-- ============================================
-- AI INSIGHTS
-- ============================================
CREATE TABLE insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_id UUID REFERENCES connected_accounts(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    
    -- Insight content
    type insight_type NOT NULL,
    priority insight_priority DEFAULT 'medium',
    title VARCHAR(500) NOT NULL,
    summary TEXT NOT NULL,
    detailed_analysis TEXT,
    
    -- AI metadata
    ai_model VARCHAR(100),
    ai_confidence DECIMAL(5, 4), -- 0.0000 to 1.0000
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    
    -- Metrics context
    metrics_snapshot JSONB, -- Snapshot of relevant metrics
    comparison_period VARCHAR(50), -- e.g., "last_7_days_vs_previous"
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,
    
    -- Validity
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insights_org ON insights(org_id);
CREATE INDEX idx_insights_account ON insights(account_id);
CREATE INDEX idx_insights_type ON insights(type);
CREATE INDEX idx_insights_priority ON insights(priority);
CREATE INDEX idx_insights_created ON insights(created_at DESC);
CREATE INDEX idx_insights_unread ON insights(org_id, is_read) WHERE is_read = FALSE;

-- ============================================
-- RECOMMENDED ACTIONS
-- ============================================
CREATE TABLE recommended_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    insight_id UUID NOT NULL REFERENCES insights(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Action details
    title VARCHAR(500) NOT NULL,
    description TEXT,
    action_type VARCHAR(100), -- pause_campaign, increase_budget, etc.
    
    -- Execution data
    platform platform_type,
    target_entity_type VARCHAR(50), -- campaign, ad_set, ad
    target_entity_id VARCHAR(255),
    
    -- Parameters for execution
    action_params JSONB DEFAULT '{}',
    
    -- Expected impact
    expected_impact TEXT,
    estimated_improvement DECIMAL(10, 2), -- Percentage or absolute value
    
    -- Status
    status action_status DEFAULT 'pending',
    executed_at TIMESTAMPTZ,
    executed_by UUID REFERENCES users(id),
    execution_result JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_actions_insight ON recommended_actions(insight_id);
CREATE INDEX idx_actions_org ON recommended_actions(org_id);
CREATE INDEX idx_actions_status ON recommended_actions(status);

-- ============================================
-- DAILY DIGESTS
-- ============================================
CREATE TABLE daily_digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Digest content
    digest_date DATE NOT NULL,
    title VARCHAR(500),
    summary TEXT NOT NULL,
    detailed_content JSONB, -- Structured sections
    
    -- Metrics summary
    total_spend_micros BIGINT,
    total_impressions BIGINT,
    total_clicks BIGINT,
    total_conversions DECIMAL(18, 4),
    
    -- Comparisons
    spend_change_percent DECIMAL(10, 2),
    impressions_change_percent DECIMAL(10, 2),
    conversions_change_percent DECIMAL(10, 2),
    
    -- Insights included
    insight_ids UUID[] DEFAULT '{}',
    
    -- Delivery
    sent_via digest_channel,
    sent_at TIMESTAMPTZ,
    delivery_status VARCHAR(50), -- sent, failed, pending
    
    -- AI metadata
    ai_model VARCHAR(100),
    tokens_used INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_digests_org ON daily_digests(org_id);
CREATE INDEX idx_digests_date ON daily_digests(digest_date);
CREATE UNIQUE INDEX idx_digests_org_date ON daily_digests(org_id, digest_date);

-- ============================================
-- SYNC JOBS (Background Job Tracking)
-- ============================================
CREATE TABLE sync_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES connected_accounts(id) ON DELETE CASCADE,
    
    -- Job info
    job_type VARCHAR(100) NOT NULL, -- daily_sync, historical_sync, manual_sync
    status sync_status DEFAULT 'pending',
    
    -- Progress
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Parameters
    date_from DATE,
    date_to DATE,
    
    -- Results
    records_synced INTEGER DEFAULT 0,
    error_message TEXT,
    error_details JSONB,
    
    -- Celery task ID
    celery_task_id VARCHAR(255),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sync_jobs_account ON sync_jobs(account_id);
CREATE INDEX idx_sync_jobs_status ON sync_jobs(status);
CREATE INDEX idx_sync_jobs_created ON sync_jobs(created_at DESC);

-- ============================================
-- API RATE LIMITS
-- ============================================
CREATE TABLE api_rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES connected_accounts(id) ON DELETE CASCADE,
    platform platform_type NOT NULL,
    
    -- Rate limit info
    requests_made INTEGER DEFAULT 0,
    requests_limit INTEGER,
    reset_at TIMESTAMPTZ,
    
    -- Last request
    last_request_at TIMESTAMPTZ,
    last_response_code INTEGER,
    
    -- Throttling
    is_throttled BOOLEAN DEFAULT FALSE,
    throttled_until TIMESTAMPTZ,
    
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(account_id, platform)
);

CREATE INDEX idx_rate_limits_account ON api_rate_limits(account_id);

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_connected_accounts_updated_at BEFORE UPDATE ON connected_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_campaigns_updated_at BEFORE UPDATE ON campaigns FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ad_sets_updated_at BEFORE UPDATE ON ad_sets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_daily_metrics_updated_at BEFORE UPDATE ON daily_metrics FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_insights_updated_at BEFORE UPDATE ON insights FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_actions_updated_at BEFORE UPDATE ON recommended_actions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_sync_jobs_updated_at BEFORE UPDATE ON sync_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

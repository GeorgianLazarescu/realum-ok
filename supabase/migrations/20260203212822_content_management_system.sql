/*
  # Content Management System (M176-180)

  1. New Tables
    - `content_items`
      - Dynamic content with versioning support
      - Support for multiple content types (article, page, lesson, etc.)
      - Rich text content storage
      - SEO metadata
    
    - `content_versions`
      - Version history for all content
      - Track changes and authors
      - Rollback capability
    
    - `content_categories`
      - Organize content into categories
      - Hierarchical category support
    
    - `content_tags`
      - Flexible tagging system
      - Tag-based content discovery
    
    - `content_media`
      - Media library for images, videos, files
      - Reusable media assets

  2. Security
    - Enable RLS on all tables
    - Content creators can manage their content
    - Admins have full access
*/

-- Content Items Table
CREATE TABLE IF NOT EXISTS content_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  slug text UNIQUE NOT NULL,
  content_type text NOT NULL DEFAULT 'article',
  content_body jsonb NOT NULL,
  excerpt text,
  featured_image text,
  author_id uuid NOT NULL REFERENCES auth.users(id),
  category_id uuid,
  status text DEFAULT 'draft',
  is_featured boolean DEFAULT false,
  seo_title text,
  seo_description text,
  seo_keywords text[],
  published_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  CONSTRAINT valid_content_type CHECK (content_type IN ('article', 'page', 'lesson', 'guide', 'tutorial', 'announcement')),
  CONSTRAINT valid_status CHECK (status IN ('draft', 'review', 'published', 'archived'))
);

-- Content Versions Table
CREATE TABLE IF NOT EXISTS content_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
  version_number integer NOT NULL,
  title text NOT NULL,
  content_body jsonb NOT NULL,
  author_id uuid NOT NULL REFERENCES auth.users(id),
  change_summary text,
  created_at timestamptz DEFAULT now(),
  UNIQUE(content_id, version_number)
);

-- Content Categories Table
CREATE TABLE IF NOT EXISTS content_categories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  slug text UNIQUE NOT NULL,
  description text,
  parent_id uuid REFERENCES content_categories(id),
  display_order integer DEFAULT 0,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now()
);

-- Content Tags Table
CREATE TABLE IF NOT EXISTS content_tags (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL UNIQUE,
  slug text UNIQUE NOT NULL,
  usage_count integer DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

-- Content Tag Mapping Table
CREATE TABLE IF NOT EXISTS content_tag_mappings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
  tag_id uuid NOT NULL REFERENCES content_tags(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  UNIQUE(content_id, tag_id)
);

-- Content Media Table
CREATE TABLE IF NOT EXISTS content_media (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  filename text NOT NULL,
  original_filename text NOT NULL,
  file_type text NOT NULL,
  file_size integer NOT NULL,
  mime_type text NOT NULL,
  url text NOT NULL,
  thumbnail_url text,
  alt_text text,
  caption text,
  uploaded_by uuid NOT NULL REFERENCES auth.users(id),
  is_public boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  CONSTRAINT valid_file_type CHECK (file_type IN ('image', 'video', 'document', 'audio'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_content_items_author ON content_items(author_id);
CREATE INDEX IF NOT EXISTS idx_content_items_status ON content_items(status) WHERE status = 'published';
CREATE INDEX IF NOT EXISTS idx_content_items_slug ON content_items(slug);
CREATE INDEX IF NOT EXISTS idx_content_items_category ON content_items(category_id);
CREATE INDEX IF NOT EXISTS idx_content_versions_content ON content_versions(content_id, version_number DESC);
CREATE INDEX IF NOT EXISTS idx_content_tag_mappings_content ON content_tag_mappings(content_id);
CREATE INDEX IF NOT EXISTS idx_content_tag_mappings_tag ON content_tag_mappings(tag_id);

-- Enable RLS
ALTER TABLE content_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_tag_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_media ENABLE ROW LEVEL SECURITY;

-- RLS Policies for content_items
CREATE POLICY "Anyone can view published content"
  ON content_items FOR SELECT
  TO authenticated
  USING (status = 'published' OR author_id = auth.uid());

CREATE POLICY "Authors can create content"
  ON content_items FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = author_id);

CREATE POLICY "Authors can update own content"
  ON content_items FOR UPDATE
  TO authenticated
  USING (auth.uid() = author_id)
  WITH CHECK (auth.uid() = author_id);

CREATE POLICY "Authors can delete own content"
  ON content_items FOR DELETE
  TO authenticated
  USING (auth.uid() = author_id);

-- RLS Policies for content_versions
CREATE POLICY "Authors can view versions of accessible content"
  ON content_versions FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM content_items
      WHERE content_items.id = content_versions.content_id
      AND (content_items.author_id = auth.uid() OR content_items.status = 'published')
    )
  );

CREATE POLICY "System can create versions"
  ON content_versions FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- RLS Policies for content_categories
CREATE POLICY "Anyone can view active categories"
  ON content_categories FOR SELECT
  TO authenticated
  USING (is_active = true);

CREATE POLICY "Admins can manage categories"
  ON content_categories FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.id = auth.uid() AND users.role = 'admin'
    )
  );

-- RLS Policies for content_tags
CREATE POLICY "Anyone can view tags"
  ON content_tags FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Users can create tags"
  ON content_tags FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- RLS Policies for content_tag_mappings
CREATE POLICY "Anyone can view tag mappings"
  ON content_tag_mappings FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authors can manage tags for own content"
  ON content_tag_mappings FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM content_items
      WHERE content_items.id = content_tag_mappings.content_id
      AND content_items.author_id = auth.uid()
    )
  );

-- RLS Policies for content_media
CREATE POLICY "Anyone can view public media"
  ON content_media FOR SELECT
  TO authenticated
  USING (is_public = true OR uploaded_by = auth.uid());

CREATE POLICY "Users can upload media"
  ON content_media FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = uploaded_by);

CREATE POLICY "Users can manage own media"
  ON content_media FOR UPDATE
  TO authenticated
  USING (auth.uid() = uploaded_by)
  WITH CHECK (auth.uid() = uploaded_by);

-- Insert default categories
INSERT INTO content_categories (name, slug, description, display_order) VALUES
  ('Tutorials', 'tutorials', 'Step-by-step guides and tutorials', 1),
  ('News', 'news', 'Platform news and announcements', 2),
  ('Guides', 'guides', 'Comprehensive guides', 3),
  ('Community', 'community', 'Community content and stories', 4)
ON CONFLICT (slug) DO NOTHING;

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    logo_path = db.Column(db.String(255))
    favicon_path = db.Column(db.String(255))
    template_project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    template_project = db.relationship('Project', foreign_keys=[template_project_id])

    @staticmethod
    def get_settings():
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        return settings

    @staticmethod
    def verify_password(password):
        return password == 'admin'

class Project(db.Model):
    __tablename__ = 'project'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    client_site_name = db.Column(db.String(100), nullable=False)
    client_site_url = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    competitor_sites = db.relationship('CompetitorSite', backref='project', lazy=True)
    pillars = db.relationship('Pillar', backref='project', lazy=True)
    crawl_configs = db.relationship('CrawlConfig', backref='project')

class CompetitorSite(db.Model):
    __tablename__ = 'competitor_site'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    crawl_configs = db.relationship('CrawlConfig', backref='site')

class Pillar(db.Model):
    __tablename__ = 'pillar'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    weight = db.Column(db.Integer, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    questions = db.relationship('Question', backref='pillar_ref', lazy=True)

    def weight_percentage(self):
        total_weight = sum([p.weight for p in self.project.pillars])
        return (self.weight / total_weight) * 100 if total_weight > 0 else 0

class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    pillar_id = db.Column(db.Integer, db.ForeignKey('pillar.id'), nullable=False)

class Evaluation(db.Model):
    __tablename__ = 'evaluation'
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('competitor_site.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer = db.Column(db.String(20), nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CrawlConfig(db.Model):
    __tablename__ = 'crawl_config'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('competitor_site.id'), nullable=True)
    max_pages = db.Column(db.Integer, default=20)
    max_depth = db.Column(db.Integer, default=2)
    delay = db.Column(db.Float, default=1.0)
    similarity_threshold = db.Column(db.Float, default=0.7)
    keywords = db.Column(db.String(500))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project = db.relationship('Project', backref='crawl_configs')
    site = db.relationship('CompetitorSite', backref='crawl_configs')
    results = db.relationship('CrawlResult', backref='config', lazy=True)

class CrawlResult(db.Model):
    __tablename__ = 'crawl_result'
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('crawl_config.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    content_hash = db.Column(db.String(64))
    keywords = db.Column(db.String(500))
    cluster = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    links = db.relationship('CrawlLink', 
                          primaryjoin="or_(CrawlResult.id==CrawlLink.source_id, CrawlResult.id==CrawlLink.target_id)",
                          lazy='dynamic')

class CrawlLink(db.Model):
    __tablename__ = 'crawl_link'
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('crawl_result.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('crawl_result.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.relationship('CrawlResult', foreign_keys=[source_id])
    target = db.relationship('CrawlResult', foreign_keys=[target_id])

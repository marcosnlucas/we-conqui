from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import asyncio
from crawler import run_crawler
import threading

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['APPLICATION_ROOT'] = '/matriz-we-conqui'
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'weconqui.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'img', 'uploads')
db = SQLAlchemy(app)

# Models
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
        return password == 'WE@2025@CONQUI'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    client_site_name = db.Column(db.String(100), nullable=False)
    client_site_url = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    competitor_sites = db.relationship('CompetitorSite', lazy=True)
    pillars = db.relationship('Pillar', lazy=True)
    crawl_configs = db.relationship('CrawlConfig', lazy=True)

class CompetitorSite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    crawl_configs = db.relationship('CrawlConfig', lazy=True)

class Pillar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    weight = db.Column(db.Integer, nullable=False)  # Peso de 1 a 10
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    questions = db.relationship('Question', lazy=True)

    @property
    def weight_percentage(self):
        total_weight = db.session.query(db.func.sum(Pillar.weight)).filter(Pillar.project_id == self.project_id).scalar() or 0
        if total_weight == 0:
            return 0
        return round((self.weight / total_weight) * 100, 2)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    weight = db.Column(db.Integer, nullable=False)  # Peso de 1 a 10
    pillar_id = db.Column(db.Integer, db.ForeignKey('pillar.id'), nullable=False)

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('competitor_site.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer = db.Column(db.String(20), nullable=False)  # 'SIM', 'NAO', ou 'PARCIALMENTE'
    weight = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# WE Crawl Models
class CrawlConfig(db.Model):
    __tablename__ = 'crawl_config'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('competitor_site.id'), nullable=True)  # Null for main site
    max_pages = db.Column(db.Integer, default=20)
    max_depth = db.Column(db.Integer, default=2)
    delay = db.Column(db.Float, default=1.0)
    similarity_threshold = db.Column(db.Float, default=0.7)
    keywords = db.Column(db.String(500))  # Comma-separated keywords
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = db.relationship('Project', foreign_keys=[project_id])
    site = db.relationship('CompetitorSite', foreign_keys=[site_id])
    results = db.relationship('CrawlResult', lazy=True)

class CrawlResult(db.Model):
    __tablename__ = 'crawl_result'
    
    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey('crawl_config.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    content_hash = db.Column(db.String(64))  # Para detectar mudanças no conteúdo
    keywords = db.Column(db.String(500))  # Keywords encontradas na página
    cluster = db.Column(db.String(100))  # Nome do cluster ao qual pertence
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

# Função auxiliar para salvar arquivos
def save_file(file, prefix=''):
    if file:
        # Cria o diretório de upload se não existir
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        filename = secure_filename(file.filename)
        if prefix:
            filename = f"{prefix}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return os.path.join('img', 'uploads', filename)
    return None

# Rotas da interface
@app.route('/')
def index():
    settings = Settings.get_settings()
    return render_template('index.html', settings=settings)

@app.route('/projects')
def projects_page():
    return render_template('projects.html')

@app.route('/project/<int:project_id>')
def project_page(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project.html', project=project)

@app.route('/project/<int:project_id>/pillars')
def pillars_page(project_id):
    project = Project.query.get_or_404(project_id)
    pillars = Pillar.query.filter_by(project_id=project_id).all()
    return render_template('pillars.html', project=project, pillars=pillars)

@app.route('/project/<int:project_id>/questions')
def questions_page(project_id):
    project = Project.query.get_or_404(project_id)
    pillars = Pillar.query.filter_by(project_id=project_id).all()
    return render_template('questions.html', project=project, pillars=pillars)

@app.route('/project/<int:project_id>/evaluate')
def evaluate(project_id):
    project = Project.query.get_or_404(project_id)
    if not project:
        flash('Projeto não encontrado', 'error')
        return redirect(url_for('index'))
    
    # Criar um "site" principal usando os dados do projeto
    main_site = {
        'id': f'main_{project_id}',  # Identificador especial para o site principal
        'name': project.client_site_name,
        'url': project.client_site_url
    }
    
    # Buscar os sites concorrentes
    competitor_sites = CompetitorSite.query.filter_by(project_id=project_id).all()
    
    # Combinar site principal e concorrentes
    all_sites = [main_site] + [{'id': site.id, 'name': site.name, 'url': site.url} for site in competitor_sites]
    
    return render_template('evaluate.html', project=project, sites=all_sites)

@app.route('/project/<int:project_id>/results')
def results(project_id):
    project = Project.query.get_or_404(project_id)
    pillars = Pillar.query.filter_by(project_id=project_id).all()
    
    # Criar um "site" principal usando os dados do projeto
    main_site = {
        'id': project_id,  # Site principal usa o project_id
        'name': project.client_site_name,
        'url': project.client_site_url,
        'is_main': True
    }
    
    # Buscar os sites concorrentes
    competitor_sites = CompetitorSite.query.filter_by(project_id=project_id).all()
    all_sites = [main_site] + [{'id': site.id, 'name': site.name, 'url': site.url, 'is_main': False} for site in competitor_sites]
    
    # Processar dados para cada site
    sites_data = []
    for site in all_sites:
        # Buscar avaliações do site
        evaluations = Evaluation.query.filter_by(site_id=site['id']).all()
        evaluations_map = {eval.question_id: eval for eval in evaluations}
        
        # Calcular soma total dos pesos dos pilares
        total_pillars_weight = sum(pillar.weight for pillar in pillars)
        
        # Processar dados dos pilares para este site
        processed_pillars = []
        total_weighted_score = 0
        
        for pillar in pillars:
            pillar_data = {
                'id': pillar.id,
                'name': pillar.name,
                'questions': [],
                'score': 0,
                'max_score': 0,
                'weight': pillar.weight,
                'weight_percentage': round((pillar.weight / total_pillars_weight * 100), 1) if total_pillars_weight > 0 else 0
            }
            
            # Processar questões do pilar
            for question in pillar.questions:
                evaluation = evaluations_map.get(question.id)
                answer = evaluation.answer if evaluation else 'NAO'
                
                # Calcular pontuação (SIM = 1x, PARCIALMENTE = 0.5x, NAO = 0x)
                multiplier = 1 if answer == 'SIM' else 0.5 if answer == 'PARCIALMENTE' else 0
                score = question.weight * multiplier
                
                pillar_data['questions'].append({
                    'id': question.id,
                    'text': question.text,
                    'weight': question.weight,
                    'answer': answer,
                    'score': score
                })
                
                pillar_data['score'] += score
                pillar_data['max_score'] += question.weight
            
            # Calcular percentual do pilar
            pillar_percentage = (pillar_data['score'] / pillar_data['max_score'] * 100) if pillar_data['max_score'] > 0 else 0
            total_weighted_score += pillar_percentage * pillar.weight
            
            processed_pillars.append(pillar_data)
        
        # Calcular pontuação total para este site
        total_score = {
            'percentage': round(total_weighted_score / total_pillars_weight if total_pillars_weight > 0 else 0, 1),
            'weighted_score': round(total_weighted_score, 1),
            'total_weight': total_pillars_weight
        }
        
        sites_data.append({
            'site': site,
            'pillars': processed_pillars,
            'total': total_score
        })
    
    # Ordenar sites: principal primeiro, depois por pontuação
    sites_data.sort(key=lambda x: (-x['site']['is_main'], -x['total']['percentage']))
    
    return render_template('results.html', 
                         project=project,
                         sites_data=sites_data)

@app.route('/settings')
def settings_page():
    settings = Settings.get_settings()
    projects = Project.query.all()
    return render_template('settings.html', settings=settings, projects=projects)

# Rotas da API
@app.route('/api/projects', methods=['GET', 'POST'])
def projects():
    if request.method == 'POST':
        data = request.get_json()
        
        project = Project(
            name=data['name'],
            client_site_name=data['client_site_name'],
            client_site_url=data['client_site_url']
        )
        
        db.session.add(project)
        
        # Adicionar sites concorrentes
        for competitor in data.get('competitors', []):
            competitor_site = CompetitorSite(
                name=competitor['name'],
                url=competitor['url'],
                project=project
            )
            db.session.add(competitor_site)
        
        try:
            db.session.commit()
            return jsonify({"message": "Projeto criado com sucesso", "id": project.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400
            
    settings = Settings.get_settings()
    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'client_site_name': p.client_site_name,
        'client_site_url': p.client_site_url,
        'competitors': [{
            'id': cs.id,
            'name': cs.name,
            'url': cs.url
        } for cs in p.competitor_sites],
        'created_at': p.created_at.isoformat(),
        'is_template': p.id == settings.template_project_id
    } for p in projects])

@app.route('/api/projects/<int:project_id>/competitors', methods=['GET'])
def project_competitors(project_id):
    competitors = CompetitorSite.query.filter_by(project_id=project_id).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'url': c.url
    } for c in competitors])

@app.route('/api/projects/<int:project_id>/pillars', methods=['GET', 'POST'])
def project_pillars(project_id):
    if request.method == 'POST':
        data = request.get_json()
        pillar = Pillar(
            name=data['name'],
            description=data.get('description', ''),
            weight=data['weight'],
            project_id=project_id
        )
        
        try:
            db.session.add(pillar)
            db.session.commit()
            return jsonify({"message": "Pilar criado com sucesso", "id": pillar.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400
    
    pillars = Pillar.query.filter_by(project_id=project_id).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'weight': p.weight,
        'weight_percentage': p.weight_percentage,
        'questions_count': len(p.questions)
    } for p in pillars])

@app.route('/api/projects/<int:project_id>/pillars/<int:pillar_id>/questions', methods=['GET', 'POST'])
def pillar_questions(project_id, pillar_id):
    if request.method == 'POST':
        data = request.get_json()
        question = Question(
            text=data['text'],
            weight=data['weight'],
            pillar_id=pillar_id
        )
        
        try:
            db.session.add(question)
            db.session.commit()
            return jsonify({"message": "Pergunta criada com sucesso", "id": question.id})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400
    
    questions = Question.query.filter_by(pillar_id=pillar_id).all()
    return jsonify([{
        'id': q.id,
        'text': q.text,
        'weight': q.weight
    } for q in questions])

@app.route('/api/project/<int:project_id>/evaluate', methods=['POST'])
def save_evaluation(project_id):
    data = request.json
    site_id = data.get('site_id')
    evaluations = data.get('evaluations', [])
    
    # Se o site_id começar com 'main_', é o site principal
    if site_id.startswith('main_'):
        actual_site_id = project_id
    else:
        actual_site_id = int(site_id)
    
    try:
        # Remover avaliações existentes para este site
        Evaluation.query.filter_by(site_id=actual_site_id).delete()
        
        # Inserir novas avaliações
        for eval_data in evaluations:
            evaluation = Evaluation(
                site_id=actual_site_id,
                question_id=eval_data['question_id'],
                answer=eval_data['answer'],
                weight=eval_data['weight']
            )
            db.session.add(evaluation)
        
        db.session.commit()
        return jsonify({'message': 'Avaliação salva com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET', 'PUT'])
def project(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': project.id,
            'name': project.name,
            'client_site_name': project.client_site_name,
            'client_site_url': project.client_site_url,
            'competitors': [{
                'id': comp.id,
                'name': comp.name,
                'url': comp.url
            } for comp in project.competitor_sites]
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        project.name = data['name']
        project.client_site_name = data['client_site_name']
        project.client_site_url = data['client_site_url']
        
        # Remove todos os concorrentes existentes
        for competitor in project.competitor_sites:
            db.session.delete(competitor)
        
        # Adiciona os novos concorrentes
        for competitor in data.get('competitors', []):
            competitor_site = CompetitorSite(
                name=competitor['name'],
                url=competitor['url'],
                project=project
            )
            db.session.add(competitor_site)
        
        try:
            db.session.commit()
            return jsonify({'message': 'Projeto atualizado com sucesso'})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400

@app.route('/api/settings', methods=['GET', 'POST'])
def update_settings():
    if request.method == 'GET':
        settings = Settings.get_settings()
        template_project = Project.query.get(settings.template_project_id) if settings.template_project_id else None
        
        return jsonify({
            'id': settings.id,
            'logo_path': settings.logo_path,
            'favicon_path': settings.favicon_path,
            'template_project_id': settings.template_project_id,
            'template_project': {
                'id': template_project.id,
                'name': template_project.name
            } if template_project else None
        })
    
    settings = Settings.get_settings()
    
    if 'logo' in request.files:
        logo = request.files['logo']
        if logo.filename:
            if settings.logo_path:
                old_path = os.path.join(basedir, 'static', settings.logo_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
            settings.logo_path = save_file(logo, 'logo')
    
    if 'favicon' in request.files:
        favicon = request.files['favicon']
        if favicon.filename:
            if settings.favicon_path:
                old_path = os.path.join(basedir, 'static', settings.favicon_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
            settings.favicon_path = save_file(favicon, 'favicon')
    
    try:
        db.session.commit()
        return jsonify({"message": "Configurações atualizadas com sucesso"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/settings/verify-password', methods=['POST'])
def verify_password():
    data = request.get_json()
    if Settings.verify_password(data.get('password')):
        return jsonify({'success': True})
    return jsonify({'success': False}), 401

@app.route('/api/settings/template-project', methods=['POST'])
def update_template_project():
    data = request.get_json()
    settings = Settings.get_settings()
    
    try:
        settings.template_project_id = data.get('project_id') or None
        db.session.commit()
        return jsonify({"message": "Projeto modelo atualizado com sucesso"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/projects/copy-template', methods=['POST'])
def copy_template_to_project():
    data = request.get_json()
    project_id = data.get('project_id')
    
    if not project_id:
        return jsonify({"error": "ID do projeto não fornecido"}), 400
    
    settings = Settings.get_settings()
    if not settings.template_project_id:
        return jsonify({"error": "Nenhum projeto modelo definido"}), 400
    
    try:
        # Busca o projeto destino e o projeto modelo
        project = Project.query.get(project_id)
        template = Project.query.get(settings.template_project_id)
        
        if not project or not template:
            return jsonify({"error": "Projeto não encontrado"}), 404
        
        # Remove pilares e questões existentes
        for pillar in project.pillars:
            for question in pillar.questions:
                db.session.delete(question)
            db.session.delete(pillar)
        
        # Copia pilares e questões do modelo
        for template_pillar in template.pillars:
            new_pillar = Pillar(
                name=template_pillar.name,
                description=template_pillar.description,
                weight=template_pillar.weight,
                project=project
            )
            db.session.add(new_pillar)
            
            for template_question in template_pillar.questions:
                new_question = Question(
                    text=template_question.text,
                    weight=template_question.weight,
                    pillar_ref=new_pillar
                )
                db.session.add(new_question)
        
        db.session.commit()
        return jsonify({"message": "Projeto atualizado com sucesso"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/projects/<int:project_id>/copy-template', methods=['POST'])
def copy_template(project_id):
    settings = Settings.get_settings()
    if not settings.template_project_id:
        return jsonify({'error': 'Nenhum projeto modelo definido'}), 400
        
    template = Project.query.get(settings.template_project_id)
    if not template:
        return jsonify({'error': 'Projeto modelo não encontrado'}), 404
        
    target = Project.query.get(project_id)
    if not target:
        return jsonify({'error': 'Projeto alvo não encontrado'}), 404
    
    try:
        # Primeiro, remove todos os pilares e questões existentes do projeto alvo
        for pillar in target.pillars:
            for question in pillar.questions:
                db.session.delete(question)
            db.session.delete(pillar)
        
        # Agora copia os pilares e questões do template para o projeto alvo
        for pillar in template.pillars:
            new_pillar = Pillar(
                name=pillar.name,
                description=pillar.description,
                weight=pillar.weight,
                project_id=target.id
            )
            db.session.add(new_pillar)
            db.session.flush()  # Para obter o ID do novo pilar
            
            # Copia as questões do pilar
            for question in pillar.questions:
                new_question = Question(
                    text=question.text,
                    weight=question.weight,
                    pillar_id=new_pillar.id
                )
                db.session.add(new_question)
        
        db.session.commit()
        return jsonify({'message': 'Template copiado com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API endpoint for managing pillars
@app.route('/api/pillars', methods=['POST'])
def create_pillar():
    data = request.json
    try:
        new_pillar = Pillar(
            name=data['name'],
            description=data.get('description', ''),
            weight=int(data['weight']),
            project_id=int(data['project_id'])
        )
        db.session.add(new_pillar)
        db.session.commit()
        return jsonify({
            "message": "Pillar created successfully",
            "id": new_pillar.id
        }), 201
    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid value: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/pillars/<int:pillar_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_pillar(pillar_id):
    pillar = Pillar.query.get_or_404(pillar_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': pillar.id,
            'name': pillar.name,
            'description': pillar.description,
            'weight': pillar.weight,
            'project_id': pillar.project_id
        })
    
    elif request.method == 'DELETE':
        db.session.delete(pillar)
        db.session.commit()
        return jsonify({"message": "Pillar deleted successfully"}), 200
    
    data = request.json
    pillar.name = data.get('name', pillar.name)
    pillar.description = data.get('description', pillar.description)
    pillar.weight = data.get('weight', pillar.weight)
    
    try:
        db.session.commit()
        return jsonify({"message": "Pillar updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

# API endpoint for managing questions
@app.route('/api/questions', methods=['POST'])
def create_question():
    data = request.json
    try:
        new_question = Question(
            text=data['text'],
            weight=int(data['weight']),
            pillar_id=int(data['pillar_id'])
        )
        db.session.add(new_question)
        db.session.commit()
        return jsonify({
            "message": "Question created successfully",
            "id": new_question.id
        }), 201
    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid value: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/questions/<int:question_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_question(question_id):
    question = Question.query.get_or_404(question_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': question.id,
            'text': question.text,
            'weight': question.weight,
            'pillar_id': question.pillar_id
        })
    
    elif request.method == 'DELETE':
        db.session.delete(question)
        db.session.commit()
        return jsonify({"message": "Question deleted successfully"}), 200
    
    data = request.json
    try:
        question.text = data['text']
        question.weight = int(data['weight'])
        question.pillar_id = int(data['pillar_id'])
        db.session.commit()
        return jsonify({"message": "Question updated successfully"}), 200
    except KeyError as e:
        return jsonify({"error": f"Missing required field: {str(e)}"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid value: {str(e)}"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

@app.route('/api/projects/<int:project_id>/questions')
def project_questions(project_id):
    project = Project.query.get_or_404(project_id)
    questions = Question.query.join(Pillar).filter(Pillar.project_id == project_id).all()
    return jsonify([{
        'id': q.id,
        'text': q.text,
        'weight': q.weight,
        'pillar_id': q.pillar_id
    } for q in questions])

@app.route('/api/settings/logo', methods=['POST'])
def update_logo():
    settings = Settings.get_settings()
    
    if 'logo' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
    logo = request.files['logo']
    if logo.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    
    if logo:
        try:
            # Remove o logo antigo se existir
            if settings.logo_path:
                old_path = os.path.join(basedir, 'static', settings.logo_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Salva o novo logo
            logo_path = save_file(logo, 'logo')
            settings.logo_path = logo_path
            db.session.commit()
            
            return jsonify({
                'message': 'Logo atualizada com sucesso',
                'logo_path': logo_path
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Erro ao processar arquivo'}), 400

@app.route('/api/settings/favicon', methods=['POST'])
def update_favicon():
    settings = Settings.get_settings()
    
    if 'favicon' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
    favicon = request.files['favicon']
    if favicon.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    
    if favicon:
        try:
            # Remove o favicon antigo se existir
            if settings.favicon_path:
                old_favicon_path = os.path.join(app.config['UPLOAD_FOLDER'], settings.favicon_path)
                if os.path.exists(old_favicon_path):
                    os.remove(old_favicon_path)
            
            # Salva o novo favicon
            favicon_path = save_file(favicon, 'favicon')
            settings.favicon_path = favicon_path
            db.session.commit()
            
            return jsonify({
                'message': 'Favicon atualizado com sucesso',
                'favicon_path': favicon_path
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Erro ao processar arquivo'}), 400

@app.route('/api/project/<int:project_id>/results')
def project_results_data(project_id):
    project = Project.query.get_or_404(project_id)
    if not project:
        return jsonify({'error': 'Projeto não encontrado'}), 404
    
    pillars_data = []
    pillars = Pillar.query.filter_by(project_id=project_id).all()
    
    for pillar in pillars:
        total_score = 0
        questions_data = []
        
        for question in pillar.questions:
            # Buscar a resposta no banco
            answer = Evaluation.query.filter_by(
                site_id=project.id,  # Usando project.id como site_id
                question_id=question.id
            ).first()
            
            score = answer.weight if answer else 0
            total_score += score
            
            questions_data.append({
                'id': question.id,
                'text': question.text,
                'score': score
            })
        
        # Calcular porcentagem do pilar (total_score / (número de questões * 5)) * 100
        pillar_score = (total_score / (len(pillar.questions) * 5)) * 100 if pillar.questions else 0
        
        pillars_data.append({
            'id': pillar.id,
            'name': pillar.name,
            'score': round(pillar_score, 1),
            'questions': questions_data
        })
    
    return jsonify({
        'project': {
            'id': project.id,
            'name': project.name
        },
        'pillars': pillars_data
    })

@app.route('/api/project/<int:project_id>')
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    return jsonify({
        'id': project.id,
        'name': project.name,
        'client_site_name': project.client_site_name,
        'client_site_url': project.client_site_url
    })

@app.route('/api/project/<int:project_id>/pillars')
def get_project_pillars(project_id):
    project = Project.query.get_or_404(project_id)
    pillars = Pillar.query.filter_by(project_id=project_id).all()
    
    pillars_data = []
    for pillar in pillars:
        questions = Question.query.filter_by(pillar_id=pillar.id).all()
        questions_data = [{
            'id': q.id,
            'text': q.text,
            'weight': q.weight
        } for q in questions]
        
        pillars_data.append({
            'id': pillar.id,
            'name': pillar.name,
            'questions': questions_data
        })
    
    return jsonify(pillars_data)

@app.route('/api/project/<int:project_id>/evaluations')
def get_project_evaluations(project_id):
    site_id = request.args.get('site_id')
    
    # Se o site_id começar com 'main_', é o site principal
    if site_id and site_id.startswith('main_'):
        evaluations = Evaluation.query.filter_by(site_id=project_id).all()
    else:
        evaluations = Evaluation.query.filter_by(site_id=site_id).all() if site_id else []
    
    return jsonify([{
        'id': eval.id,
        'question_id': eval.question_id,
        'answer': eval.answer,
        'weight': eval.weight
    } for eval in evaluations])

@app.route('/api/project/<int:project_id>/results')
def get_project_results(project_id):
    project = Project.query.get_or_404(project_id)
    pillars = Pillar.query.filter_by(project_id=project_id).all()
    
    # Criar um "site" principal usando os dados do projeto
    main_site = {
        'id': project_id,  # Site principal usa o project_id
        'name': project.client_site_name,
        'url': project.client_site_url,
        'is_main': True
    }
    
    # Buscar os sites concorrentes
    competitor_sites = CompetitorSite.query.filter_by(project_id=project_id).all()
    all_sites = [main_site] + [{'id': site.id, 'name': site.name, 'url': site.url, 'is_main': False} for site in competitor_sites]
    
    # Processar dados para cada site
    sites_data = []
    for site in all_sites:
        # Buscar avaliações do site
        evaluations = Evaluation.query.filter_by(site_id=site['id']).all()
        evaluations_map = {eval.question_id: eval for eval in evaluations}
        
        # Calcular soma total dos pesos dos pilares
        total_pillars_weight = sum(pillar.weight for pillar in pillars)
        
        # Processar dados dos pilares para este site
        processed_pillars = []
        total_weighted_score = 0
        
        for pillar in pillars:
            pillar_data = {
                'id': pillar.id,
                'name': pillar.name,
                'score': 0,
                'max_score': 0,
                'weight': pillar.weight,
                'weight_percentage': round((pillar.weight / total_pillars_weight * 100), 1) if total_pillars_weight > 0 else 0
            }
            
            # Processar questões do pilar
            for question in pillar.questions:
                evaluation = evaluations_map.get(question.id)
                answer = evaluation.answer if evaluation else 'NAO'
                
                # Calcular pontuação (SIM = 1x, PARCIALMENTE = 0.5x, NAO = 0x)
                multiplier = 1 if answer == 'SIM' else 0.5 if answer == 'PARCIALMENTE' else 0
                score = question.weight * multiplier
                
                pillar_data['score'] += score
                pillar_data['max_score'] += question.weight
            
            # Calcular pontuação ponderada do pilar
            pillar_weighted_score = (pillar_data['score'] / pillar_data['max_score']) * pillar.weight if pillar_data['max_score'] > 0 else 0
            total_weighted_score += pillar_weighted_score
            
            processed_pillars.append(pillar_data)
        
        # Calcular pontuação total em porcentagem
        total_percentage = (total_weighted_score / total_pillars_weight * 100) if total_pillars_weight > 0 else 0
        
        sites_data.append({
            'site': site,
            'pillars': processed_pillars,
            'total_score': total_weighted_score,
            'total_percentage': round(total_percentage, 1)
        })
    
    return jsonify({
        'project_id': project.id,
        'project_name': project.name,
        'pillars': sites_data
    })

# Rotas do WE Crawl
@app.route('/project/<int:project_id>/crawl')
def crawl_config(project_id):
    project = Project.query.get_or_404(project_id)
    configs = CrawlConfig.query.filter_by(project_id=project_id).order_by(CrawlConfig.created_at.desc()).all()
    return render_template('crawl_config.html', project=project, configs=configs)

# Criar um único event loop para toda a aplicação
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Função para rodar o event loop em uma thread separada
def run_event_loop():
    loop.run_forever()

# Iniciar o event loop em uma thread separada
event_loop_thread = threading.Thread(target=run_event_loop, daemon=True)
event_loop_thread.start()

@app.route('/api/crawl/<int:project_id>/save', methods=['POST'])
def save_crawl_config(project_id):
    site_id = request.form.get('site_id')
    keywords = request.form.get('keywords', '')
    max_pages = request.form.get('max_pages', 20)
    max_depth = request.form.get('max_depth', 2)
    
    config = CrawlConfig(
        project_id=project_id,
        site_id=site_id if site_id != 'client' else None,
        keywords=keywords,
        max_pages=max_pages,
        max_depth=max_depth,
        status='pending'
    )
    
    db.session.add(config)
    db.session.commit()
    
    # Pegar nome do site
    if site_id == 'client':
        site_name = config.project.client_site_name
    else:
        site = CompetitorSite.query.get(site_id)
        site_name = site.name if site else ''
    
    return jsonify({
        'success': True,
        'config': {
            'id': config.id,
            'site_name': site_name,
            'status': config.status
        }
    })

@app.route('/project/<int:project_id>/crawl/<int:config_id>/results')
def crawl_results(project_id, config_id):
    project = Project.query.get_or_404(project_id)
    config = CrawlConfig.query.get_or_404(config_id)
    
    if config.project_id != project_id:
        abort(404)
    
    return render_template('crawl_results.html', project=project, config=config)

@app.route('/project/<int:project_id>/crawl/<int:config_id>/graph')
def crawl_graph_data(project_id, config_id):
    project = Project.query.get_or_404(project_id)
    config = CrawlConfig.query.get_or_404(config_id)
    
    if config.project_id != project_id:
        abort(404)
    
    # Construir o grafo a partir dos resultados
    import networkx as nx
    import plotly.graph_objects as go
    
    G = nx.Graph()
    
    # Adicionar nós (URLs)
    for result in config.results:
        G.add_node(result.url)
    
    # Adicionar arestas (links)
    for result in config.results:
        for link in result.links:
            G.add_edge(link.source.url, link.target.url)
    
    # Gerar layout do grafo
    pos = nx.spring_layout(G)
    
    # Preparar dados para o Plotly
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    
    node_x = []
    node_y = []
    node_text = []
    node_color = []
    
    # Mapear clusters para cores
    clusters = {}
    current_cluster = 0
    
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        
        # Encontrar o cluster deste nó
        result = CrawlResult.query.filter_by(config_id=config.id, url=node).first()
        cluster = result.cluster if result else 'Unknown'
        
        if cluster not in clusters:
            clusters[cluster] = current_cluster
            current_cluster += 1
        
        node_color.append(clusters[cluster])
        node_text.append(f'URL: {node}<br>Cluster: {cluster}')
    
    # Criar o gráfico
    data = [
        # Arestas
        go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        ),
        # Nós
        go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                showscale=True,
                colorscale='Viridis',
                color=node_color,
                size=10,
                colorbar=dict(
                    thickness=15,
                    title='Cluster',
                    xanchor='left',
                    titleside='right'
                ),
                line_width=2
            )
        )
    ]
    
    layout = go.Layout(
        title='Gráfico de Clusters',
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20,l=5,r=5,t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        template='plotly_white'
    )
    
    return jsonify({
        'data': data,
        'layout': layout
    })

@app.route('/crawl/<int:config_id>', methods=['POST'])
async def start_crawl(config_id):
    from crawler import run_crawler
    try:
        await run_crawler(config_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API do WE Crawler
@app.route('/api/crawl/status')
def crawl_status():
    configs = CrawlConfig.query.all()
    results = []
    for config in configs:
        # Contar páginas visitadas
        visited_pages = CrawlResult.query.filter_by(config_id=config.id).count()
        results.append({
            'id': config.id,
            'status': config.status,
            'visited_pages': visited_pages
        })
    return jsonify(results)

@app.route('/api/crawl/<int:config_id>/start', methods=['POST'])
def start_crawl_api(config_id):
    config = CrawlConfig.query.get_or_404(config_id)
    
    # Atualizar status
    config.status = 'running'
    db.session.commit()
    
    # Iniciar o crawler em uma task
    loop.call_soon_threadsafe(lambda: loop.create_task(run_crawler(config.id)))
    
    return jsonify({'success': True})

@app.route('/api/crawl/<int:config_id>/stop', methods=['POST'])
def stop_crawl(config_id):
    config = CrawlConfig.query.get_or_404(config_id)
    
    # Atualizar status
    config.status = 'stopped'
    db.session.commit()
    
    # TODO: Implementar lógica para parar o crawler
    # Por enquanto apenas atualiza o status
    
    return jsonify({'success': True})

@app.route('/api/crawl/<int:config_id>/continue', methods=['POST'])
def continue_crawl(config_id):
    config = CrawlConfig.query.get_or_404(config_id)
    
    # Atualizar status
    config.status = 'running'
    db.session.commit()
    
    # Reiniciar o crawler
    loop.call_soon_threadsafe(lambda: loop.create_task(run_crawler(config.id)))
    
    return jsonify({'success': True})

@app.route('/api/crawl/<int:config_id>', methods=['DELETE'])
def delete_crawl(config_id):
    config = CrawlConfig.query.get_or_404(config_id)
    
    # Remover resultados
    for result in config.results:
        db.session.delete(result)
    
    # Remover configuração
    db.session.delete(config)
    db.session.commit()
    
    return jsonify({'success': True})

@app.context_processor
def inject_settings():
    return dict(settings=Settings.get_settings())

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001, debug=True)

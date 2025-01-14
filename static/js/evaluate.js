document.addEventListener('DOMContentLoaded', function() {
    // Carregar dados do site e perguntas
    const siteId = new URLSearchParams(window.location.search).get('site_id');
    loadSiteData(siteId);
    loadQuestions();

    // Gerenciar pesos dos pilares
    const pesoConteudo = document.getElementById('pesoConteudo');
    const pesoEEAT = document.getElementById('pesoEEAT');

    pesoConteudo.addEventListener('input', function() {
        pesoEEAT.value = 100 - parseInt(this.value);
    });

    pesoEEAT.addEventListener('input', function() {
        pesoConteudo.value = 100 - parseInt(this.value);
    });

    // Gerenciar botões de resposta
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('answer-btn')) {
            const questionCard = e.target.closest('.question-card');
            const buttons = questionCard.querySelectorAll('.answer-btn');
            
            buttons.forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
        }
    });

    // Gerenciar salvamento
    document.getElementById('btnSalvar').addEventListener('click', function() {
        const modal = new bootstrap.Modal(document.getElementById('saveModal'));
        modal.show();
    });

    document.getElementById('btnConfirmarSalvar').addEventListener('click', function() {
        saveEvaluation();
    });

    document.getElementById('btnVoltar').addEventListener('click', function() {
        window.location.href = '/';
    });
});

async function loadSiteData(siteId) {
    try {
        const response = await fetch(`/api/sites/${siteId}`);
        const site = await response.json();
        document.getElementById('siteName').textContent = site.name;
    } catch (error) {
        console.error('Erro ao carregar dados do site:', error);
    }
}

async function loadQuestions() {
    try {
        const response = await fetch('/api/questions');
        const questions = await response.json();
        
        const contentQuestions = questions.filter(q => q.pillar === 'content_structure');
        const eeatQuestions = questions.filter(q => q.pillar === 'eeat');

        renderQuestions('contentQuestions', contentQuestions);
        renderQuestions('eeatQuestions', eeatQuestions);
    } catch (error) {
        console.error('Erro ao carregar perguntas:', error);
    }
}

function renderQuestions(containerId, questions) {
    const container = document.getElementById(containerId);
    
    questions.forEach(question => {
        const questionHtml = `
            <div class="question-card card mb-3" data-question-id="${question.id}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="card-title mb-0">${question.text}</h5>
                        <div class="question-weight">
                            <label>Peso:</label>
                            <input type="number" class="form-control form-control-sm" 
                                   value="${question.weight}" min="1" max="10" style="width: 70px">
                        </div>
                    </div>
                    <div class="btn-group d-flex justify-content-center" role="group">
                        <button type="button" class="btn btn-success answer-btn" data-answer="SIM">SIM</button>
                        <button type="button" class="btn btn-danger answer-btn" data-answer="NAO">NÃO</button>
                        <button type="button" class="btn btn-warning answer-btn" data-answer="PARCIALMENTE">PARCIALMENTE</button>
                    </div>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', questionHtml);
    });
}

async function saveEvaluation() {
    const siteId = new URLSearchParams(window.location.search).get('site_id');
    const evaluation = {
        site_id: siteId,
        pillar_weights: {
            content_structure: parseInt(document.getElementById('pesoConteudo').value),
            eeat: parseInt(document.getElementById('pesoEEAT').value)
        },
        answers: []
    };

    // Coletar todas as respostas
    document.querySelectorAll('.question-card').forEach(card => {
        const questionId = card.dataset.questionId;
        const selectedAnswer = card.querySelector('.answer-btn.active');
        const weight = card.querySelector('.question-weight input').value;

        if (selectedAnswer) {
            evaluation.answers.push({
                question_id: questionId,
                answer: selectedAnswer.dataset.answer,
                weight: parseInt(weight)
            });
        }
    });

    try {
        const response = await fetch('/api/evaluations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(evaluation)
        });

        if (response.ok) {
            window.location.href = '/results';
        } else {
            alert('Erro ao salvar a avaliação. Por favor, tente novamente.');
        }
    } catch (error) {
        console.error('Erro ao salvar avaliação:', error);
        alert('Erro ao salvar a avaliação. Por favor, tente novamente.');
    }
}

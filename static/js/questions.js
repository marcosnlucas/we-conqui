document.addEventListener('DOMContentLoaded', function() {
    // Get project_id from URL path
    const pathParts = window.location.pathname.split('/');
    const projectId = pathParts[pathParts.indexOf('project') + 1];
    
    if (!projectId) {
        alert('Erro: ID do projeto não encontrado');
        return;
    }

    loadQuestions();
    
    // Formulário de nova pergunta
    document.getElementById('questionForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const questionData = {
            text: document.getElementById('questionText').value,
            pillar_id: parseInt(document.getElementById('pillar').value),
            weight: parseInt(document.getElementById('weight').value)
        };
        
        fetch('/api/questions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(questionData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Erro ao cadastrar pergunta: ' + data.error);
            } else {
                loadQuestions();
                document.getElementById('questionForm').reset();
                bootstrap.Collapse.getInstance(document.getElementById('newQuestionForm')).hide();
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao cadastrar pergunta');
        });
    });

    // Salvar edição
    document.getElementById('btnSaveEdit').addEventListener('click', function() {
        const questionId = document.getElementById('editQuestionId').value;
        const questionData = {
            text: document.getElementById('editQuestionText').value,
            pillar_id: parseInt(document.getElementById('editPillar').value),
            weight: parseInt(document.getElementById('editWeight').value)
        };

        fetch(`/api/questions/${questionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(questionData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Erro ao atualizar pergunta: ' + data.error);
            } else {
                loadQuestions();
                bootstrap.Modal.getInstance(document.getElementById('editQuestionModal')).hide();
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao atualizar pergunta');
        });
    });

    // Excluir pergunta
    document.getElementById('btnDeleteQuestion').addEventListener('click', function() {
        if (!confirm('Tem certeza que deseja excluir esta pergunta?')) {
            return;
        }

        const questionId = document.getElementById('editQuestionId').value;
        
        fetch(`/api/questions/${questionId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Erro ao excluir pergunta: ' + data.error);
            } else {
                loadQuestions();
                bootstrap.Modal.getInstance(document.getElementById('editQuestionModal')).hide();
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao excluir pergunta');
        });
    });
});

function loadQuestions() {
    const projectId = window.location.pathname.split('/')[window.location.pathname.split('/').indexOf('project') + 1];
    const container = document.getElementById('questions-container');
    
    if (!container) {
        console.error('Container de perguntas não encontrado');
        return;
    }

    // First load pillars
    fetch(`/api/projects/${projectId}/pillars`)
        .then(response => response.json())
        .then(pillars => {
            // Clear container
            container.innerHTML = '';
            
            // Create section for each pillar
            pillars.forEach(pillar => {
                const pillarSection = document.createElement('div');
                pillarSection.className = 'col-md-6 mb-4';
                pillarSection.innerHTML = `
                    <div class="card">
                        <div class="card-header bg-conqui text-white">
                            <h5 class="mb-0">${pillar.name}</h5>
                        </div>
                        <div class="card-body">
                            <div id="questions-${pillar.id}" class="questions-list">
                                <p class="text-muted">Carregando perguntas...</p>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(pillarSection);
            });

            // Then load questions
            return fetch(`/api/projects/${projectId}/questions`);
        })
        .then(response => response.json())
        .then(questions => {
            // Group questions by pillar
            const questionsByPillar = {};
            questions.forEach(question => {
                if (!questionsByPillar[question.pillar_id]) {
                    questionsByPillar[question.pillar_id] = [];
                }
                questionsByPillar[question.pillar_id].push(question);
            });

            // Render questions for each pillar
            Object.entries(questionsByPillar).forEach(([pillarId, pillarQuestions]) => {
                const questionsList = document.getElementById(`questions-${pillarId}`);
                if (questionsList) {
                    renderQuestionsList(questionsList, pillarQuestions);
                }
            });
        })
        .catch(error => {
            console.error('Erro ao carregar dados:', error);
            alert('Erro ao carregar dados');
            if (container) {
                container.innerHTML = '<div class="alert alert-danger">Erro ao carregar perguntas. Por favor, tente novamente.</div>';
            }
        });
}

function renderQuestionsList(container, questions) {
    if (!questions || questions.length === 0) {
        container.innerHTML = '<p class="text-muted">Nenhuma pergunta cadastrada</p>';
        return;
    }

    container.innerHTML = questions.map(question => `
        <div class="question-item mb-2 p-2 border rounded">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${question.text}</strong>
                    <br>
                    <small class="text-muted">Peso: ${question.weight}</small>
                </div>
                <button class="btn btn-sm btn-outline-conqui" onclick="editQuestion(${question.id})">
                    <i class="bi bi-pencil"></i>
                </button>
            </div>
        </div>
    `).join('');
}

function editQuestion(questionId) {
    fetch(`/api/questions/${questionId}`)
        .then(response => response.json())
        .then(question => {
            document.getElementById('editQuestionId').value = question.id;
            document.getElementById('editQuestionText').value = question.text;
            document.getElementById('editPillar').value = question.pillar_id;
            document.getElementById('editWeight').value = question.weight;
            
            new bootstrap.Modal(document.getElementById('editQuestionModal')).show();
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao carregar dados da pergunta');
        });
}

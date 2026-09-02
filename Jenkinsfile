def notifyDiscord(String credId, String message) {
    withCredentials([string(credentialsId: credId, variable: 'DISCORD_WEBHOOK_URL')]) {
        sh """
            curl -sS -X POST -H "Content-Type: application/json" \\
              -d '{"content": "${message}"}' \\
              "\$DISCORD_WEBHOOK_URL" || true
        """
    }
}

pipeline {
    agent any

    environment {
        GIT_URL = 'https://github.com/Do-Meok/Back.git'
        DOCKER_IMAGE = 'augustzer0/do-meok'
        GIT_CRED_ID = 'github-login'
        DOCKER_CRED_ID = 'dockerhub-login'
        ENV_CRED_ID = 'domeok-env-file'
        DEPLOY_PATH = '/home/augustzer0/zer0/domeok'
        DISCORD_WEBHOOK_CRED_ID = 'domeok-discord-webhook'
    }

    stages {
        stage('1. 코드 불러오기') {
            steps {
                echo 'Do-Meok/Back 저장소의 main 브랜치 코드를 가져오는 중...'
                git branch: 'main', credentialsId: "${GIT_CRED_ID}", url: "${GIT_URL}"
            }
        }

        stage('2. .env 파일 생성') {
            steps {
                script {
                    echo 'Secret File 자격 증명으로부터 .env 파일 생성 중'
                    withCredentials([file(credentialsId: "${ENV_CRED_ID}", variable: 'SECRET_ENV')]) {
                        sh 'cp "$SECRET_ENV" .env'
                        // docker compose(app 배포/마이그레이션)는 ${DEPLOY_PATH}를 기준으로 .env를 읽으므로 그 경로에도 최신 값을 반영
                        sh "cp \"\$SECRET_ENV\" ${DEPLOY_PATH}/.env"
                    }
                }
            }
        }

        stage('3. 이미지 빌드') {
            steps {
                echo "Docker 이미지 빌드 중: ${DOCKER_IMAGE}:latest"
                sh "docker build -t ${DOCKER_IMAGE}:latest ."
            }
        }

        stage('4. 테스트 진행 (pytest)') {
            steps {
                echo '임시 컨테이너에서 pytest 단위 테스트 실행 중...'
                sh """
                    docker run --rm ${DOCKER_IMAGE}:latest \
                      sh -c "uv sync --frozen --group dev --no-cache && uv run pytest"
                """
            }
        }

        stage('5. 도커 허브 푸시') {
            steps {
                script {
                    echo "Docker Hub에 이미지 푸시 중: ${DOCKER_IMAGE}:latest"
                    withCredentials([usernamePassword(
                        credentialsId: "${DOCKER_CRED_ID}",
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PW'
                    )]) {
                        sh 'echo "$DOCKER_PW" | docker login -u "$DOCKER_USER" --password-stdin'
                        sh "docker push ${DOCKER_IMAGE}:latest"
                    }
                }
            }
        }

        stage('6. 배포 (compose app)') {
            steps {
                dir("${DEPLOY_PATH}") {
                    echo '최신 애플리케이션 이미지 수신 및 컨테이너 재시작 중...'
                    sh 'docker compose pull app'
                    sh 'docker compose up -d app'
                    sh 'docker image prune -f'
                }
            }
        }

        stage('7. DB 마이그레이션 (alembic)') {
            steps {
                dir("${DEPLOY_PATH}") {
                    echo '실행 중인 컨테이너에서 Alembic DB 마이그레이션 진행...'
                    // 이미 뜬 컨테이너(domeok-back) 내부에서 exec로 실행
                    sh 'docker compose exec -T app uv run alembic upgrade head'
                }
            }
        }

        stage('8. 상태 확인') {
            steps {
                script {
                    echo '컨테이너 시작 대기 후 FastAPI 헬스 체크 진행 중...'
                    sleep 10
                    sh '''
                        docker exec domeok-back python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
                    '''
                }
            }
        }
    }

    post {
        success {
            script {
                echo '배포 성공 - Discord 알림 전송 중...'
                notifyDiscord(DISCORD_WEBHOOK_CRED_ID,
                    "✅ **Do-Meok/Back** 배포 성공\\n- Job: ${env.JOB_NAME}\\n- Build: #${env.BUILD_NUMBER}\\n- URL: ${env.BUILD_URL}")
            }
        }
        failure {
            script {
                echo '배포 실패 - Discord 알림 전송 중...'
                notifyDiscord(DISCORD_WEBHOOK_CRED_ID,
                    "❌ **Do-Meok/Back** 배포 실패\\n- Job: ${env.JOB_NAME}\\n- Build: #${env.BUILD_NUMBER}\\n- URL: ${env.BUILD_URL}")
            }
        }
        always {
            echo '임시 비밀 설정 파일 삭제 및 Docker 로그인 세션 종료 중...'
            sh 'rm -f .env'
            sh 'docker logout || true'
        }
    }
}
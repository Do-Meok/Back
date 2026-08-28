pipeline {
    agent any

    environment {
        GIT_URL = 'https://github.com/Do-Meok/Back.git'
        DOCKER_IMAGE = 'augustzer0/do-meok'
        GIT_CRED_ID = 'github-login'
        DOCKER_CRED_ID = 'dockerhub-login'
        ENV_CRED_ID = 'domeok-env-file'
        DEPLOY_PATH = '/home/augustzer0/zer0/domeok'
    }

    stages {
        stage('1. Checkout') {
            steps {
                echo 'Do-Meok/Back 저장소의 main 브랜치 코드를 가져오는 중...'
                git branch: 'main', credentialsId: "${GIT_CRED_ID}", url: "${GIT_URL}"
            }
        }

        stage('2. Create .env File') {
            steps {
                script {
                    echo 'Secret File 자격 증명으로부터 작업 공간 .env 파일 생성 중'
                    withCredentials([file(credentialsId: "${ENV_CRED_ID}", variable: 'SECRET_ENV')]) {
                        sh 'cp "$SECRET_ENV" .env'
                    }
                }
            }
        }

        stage('3. Build Image') {
            steps {
                echo "Docker 이미지 빌드 중: ${DOCKER_IMAGE}:latest"
                sh "docker build -t ${DOCKER_IMAGE}:latest ."
            }
        }

        stage('4. Test (pytest)') {
            steps {
                echo '임시 컨테이너에서 pytest 단위 테스트 실행 중...'
                sh """
                    docker run --rm ${DOCKER_IMAGE}:latest \
                      sh -c "uv sync --frozen --group dev --no-cache && uv run pytest"
                """
            }
        }

        stage('5. Push to Docker Hub') {
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

        stage('6. Migrate (alembic)') {
            steps {
                echo '배포 경로로 docker-compose.yml 및 .env 파일 동기화 중...'
                sh "cp docker-compose.yml ${DEPLOY_PATH}/docker-compose.yml"
                sh "cp .env ${DEPLOY_PATH}/.env"
                dir("${DEPLOY_PATH}") {
                    echo '최신 애플리케이션 이미지 수신 및 Alembic DB 마이그레이션 실행 중...'
                    sh 'docker compose pull app'
                    sh 'docker compose run --rm app uv run alembic upgrade head'
                }
            }
        }

        stage('7. Deploy (compose app)') {
            steps {
                dir("${DEPLOY_PATH}") {
                    echo '애플리케이션 컨테이너 재시작 및 미사용 이미지 정리 중...'
                    sh 'docker compose up -d app'
                    sh 'docker image prune -f'
                }
            }
        }

        stage('8. Health Check') {
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
        always {
            echo '임시 비밀 설정 파일 삭제 및 Docker 로그인 세션 종료 중...'
            sh 'rm -f .env'
            sh 'docker logout || true'
        }
    }
}
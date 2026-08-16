# process.md - BPT 문서화 및 기여 근거 기록

전체 계획은 `plan.md`를 따른다.

표기 체계: **확인됨** / **추정** / **미확인** / **사용자 확인**

## 0. 검토 개요

- 검토일: 2026-08-17
- 대상: `BPT-unified`
- 프로젝트 성격: 3인 캡스톤 팀 프로젝트, 모바일 제품 구현 및 AI 적용·통합
- 현재 상태: **진행 중**. 캡스톤 디자인 I 결과는 1차 구현 마일스톤이며 프로젝트 종료가 아님
- README 언어: 기존 저장소 흐름과 외부 기술 검토자를 고려해 영문 유지
- 원본 최종 보고서: 24쪽 전체 검토, 개인정보가 있어 저장소에는 미복사

## 1. 사용한 근거

### 1.1 최종 보고서

캡스톤 디자인 I 최종결과 보고서에서 다음을 확인했다.

- **확인됨**: 프로젝트명은 AI 기반 자세 분석 트레이닝 앱 BPT다.
- **확인됨**: 보고서에는 전준, 서진정, 최한민 3인이 팀원으로 기재되어 있다.
- **확인됨**: Flutter, iOS Native Swift/CoreML, Firebase를 결합한 구조다.
- **확인됨**: 앱의 최종 자세 평가는 RTMPose-s 기반 2D COCO17 keypoint를 사용한다.
- **확인됨**: 스쿼트, 벤치프레스, 데드리프트, 바벨로우, 푸쉬업 평가기를 구현했다.
- **확인됨**: MediaPipe Hand Landmarker는 손 시각화와 손목 보정용 보조 구성요소다.
- **확인됨**: 3D temporal pose는 검토·설계 단계이며 최종 앱 평가 경로에서는 비활성이다.
- **확인됨**: Android 실시간 AI, 운동 영상 다시보기, 음성 피드백, 소셜 로그인, 관리자 대시보드는 미구현 또는 후속 단계다.
- **확인됨**: FPS, 지연 시간, frame drop, 자세 판정 정확도의 기기별 정량 자료는 보고서에 없다.
- **미확인**: 보고서에는 팀원별 상세 역할 분담표가 없다.

PDF metadata의 작성자 값은 `6_month`이지만, 이 값만으로 보고서 본문이나 전체 구현을 개인 기여로 귀속하지 않았다.

### 1.2 Git history

원본 BPT history에서 확인한 author identity는 다음과 같다.

| Identity | 관찰된 주된 범위 | 판단 |
| --- | --- | --- |
| `06-month`, `6-month`, `Jun` | AI 연구 브랜치, 네이티브 pose 통합, 프리뷰 수정 | 저장소 소유자 identity로 확인됨 |
| `jinjeonz` | Flutter 초기 화면, 운동 선택, 프로필·리포트, 로컬 인증·상태 개선 | 팀원 작업으로 확인됨 |
| `Han-min` | Firebase 연동, 데이터 연결, 병합 및 충돌 해결 | 팀원 작업으로 확인됨 |

기여 판단에 사용한 핵심 커밋은 다음과 같다.

| Commit | Author | 확인된 변경 |
| --- | --- | --- |
| `08d68c5` | `06-month` | 온디바이스 자세·손목 피드백 연구 구조, 변환·비교·진단 자료와 Python 모듈 도입 |
| `3394f6c` | `06-month` | Swift/CoreML 카메라 파이프라인, 평가기 5종, MediaPipe hand branch, Flutter PlatformView/MethodChannel 통합 |
| `4bc3865` | `06-month` | 네이티브 카메라 프리뷰 및 Flutter workout screen 안정화 |

`3394f6c`는 네이티브 AI 관련 42개 파일에 약 8,774줄을 추가한 변경이다. 숫자 자체를 기여 비율로 사용하지 않고, 변경된 모듈의 범위를 확인하는 보조 근거로만 사용했다.

### 1.3 실제 소스

| Claim | 코드 근거 | 상태 |
| --- | --- | --- |
| 지원 운동은 5종 | `NativePoseExercise.swift`, `native_pose_workout_screen.dart` | 확인됨 |
| 카메라→CoreML→SimCC→평가기 흐름 | `CameraPosePreview.swift`와 `PosePipeline/` | 확인됨 |
| Flutter-native 경계 | `NativePoseCameraPlatformView.swift`, per-view MethodChannel | 확인됨 |
| 프레임 안정화 | evaluator별 candidate state, confirmation frame, phase state | 확인됨 |
| 손 branch는 보조 기능 | `enableHandBranchForCamera=true`, overlay와 wrist 보정 코드 | 확인됨 |
| 3D app path 비활성 | `enableMotion3DForCamera=false` | 확인됨 |
| native 결과는 rep 중심 | Flutter handler가 `rep`만 set 진행에 사용하고 결과의 correct/incorrect/score는 `null` 전달 | 확인됨 |

### 1.4 사용자 확인 및 관련 데이터셋 저장소

2026-08-17 사용자 확인으로 보고서에 없던 역할 정보가 보완되었다.

- **사용자 확인**: 운동 데이터 촬영은 세 팀원이 모두 함께 수행했다.
- **사용자 확인**: 저장소 소유자가 데이터셋 생성 파이프라인을 설계하고 실제 구현까지 완료했다.
- **사용자 확인**: 저장소 소유자가 BPT AI pipeline과 mobile native 구현을 완료했다.
- **사용자 확인**: 현재 구현은 완료된 1차 범위지만 BPT 전체 프로젝트는 한계 확인 후 계속 개발 중이다.

별도 저장소 `06-month/Exercise3D-Dataset-Pipeline`의 Git history와 산출물로 다음을 추가 확인했다.

| 항목 | 근거 | 상태 |
| --- | --- | --- |
| 파이프라인 구현 identity | 120개 `06-month` commit과 4개 `Jun` merge commit, 다른 author 없음 | 확인됨 |
| 입력 규모 | 3명, 26개 synchronized triple-view sequence, 78 camera view | 확인됨 |
| working frame | 65,595장 | 확인됨 |
| 처리 단계 | sync, camera geometry, Sapiens2, triangulation, SAM 3D Body, body fitting, quality/freeze | 확인됨 |
| 현재 상태 | 24/26 freeze-ready, REVIEW 24 / FAIL 0 | 확인됨 |
| 공개 경계 | 원본 RGB·얼굴·개인정보·checkpoint 비공개, 코드·집계·mesh-only preview 공개 | 확인됨 |

커밋 수는 구현 주체가 단일 identity 집합임을 확인하는 근거이며, 작업량의 정량 비율로 사용하지 않는다.

## 2. 기존 README 평가

### 명확했던 점

- 통합 저장소의 주요 디렉터리를 짧게 설명했다.
- Flutter/iOS 및 Python 설치 명령이 실제 경로와 대체로 일치했다.
- 큰 연구 자산과 생성 파일을 Git에서 제외한다는 정책이 있었다.

### 부족했던 점

- 제품이 해결하는 문제와 실제 사용자 흐름이 없었다.
- 카메라에서 Flutter HUD까지 이어지는 runtime architecture가 없었다.
- 최종 앱의 5개 운동 평가기와 연구용 `pushup_side` 손목 MVP가 구분되지 않았다.
- 팀 결과와 저장소 소유자의 확인 가능한 개인 기여가 구분되지 않았다.
- 구현된 기능과 미구현 기능, 정량 근거가 없는 항목이 드러나지 않았다.
- 앱 검증 결과와 네이티브 결과 전달의 현재 제한이 없었다.

## 3. 기여 재구성

### 3.1 저장소 소유자에게 귀속 가능한 범위

Git author와 변경 파일을 함께 확인할 수 있는 범위다.

- RTMPose-s와 대안 pose/3D 모델 조사, 변환, 비교, 진단 도구
- RTMPose-s CoreML 모델의 입력 전처리와 SimCC 후처리
- affine 역변환, preview coordinate mapping, selfie mirror 처리
- AVFoundation 실시간 카메라 입력과 CoreML 추론 연결
- 스쿼트, 벤치프레스, 데드리프트, 바벨로우, 푸쉬업 평가기
- 반복 판정을 위한 phase state, candidate accumulation, consecutive-frame gate
- MediaPipe Hand Landmarker 보조 branch와 overlay
- Flutter `UiKitView`, per-view MethodChannel, set/rep 진행 연결
- 네이티브 카메라 preview 오류 수정 및 결과 화면 연결 안정화
- Python reference pipeline과 단위·파이프라인 테스트
- synchronized three-camera video를 3D pseudo-label dataset으로 변환하는 end-to-end pipeline
- camera stability audit, VGGT initialization, Background BA, Sapiens2 target pose, triangulation, SAM body prior, sequence fitting, quality gate와 private export

### 3.2 팀 결과로만 서술한 범위

다음은 보고서의 완성 기능이지만 다른 author의 커밋이 함께 확인되므로 저장소 소유자의 단독 작업으로 쓰지 않았다.

- Flutter 화면 전반과 디자인 시스템
- Riverpod 기반 인증·프로필·리포트 상태 관리
- Firebase Authentication 및 Cloud Firestore 연동
- SharedPreferences fallback과 사용자 정보 복원
- 운동 기록 CRUD, 통계 차트, 다국어 UI
- 카메라 위치 안내 이미지와 일반 운동 선택 UX
- 3대 카메라를 이용한 운동 데이터 촬영 자체는 세 팀원의 공동 작업

### 3.3 외부 또는 upstream 기술

- RTMPose-s와 MMPose 계열 model configuration
- Apple CoreML 및 AVFoundation
- Google MediaPipe Hand Landmarker
- Flutter, Riverpod, go_router, Firebase, fl_chart
- MotionAGFormer 및 기타 2D-to-3D 연구 구현
- VGGT-Ω, Sapiens2 Pose 5B, SAM 3D Body / SAM-Body4D

README에서는 이 기술을 조사·변환·적용·통합한 것으로 서술하며, 모델 자체를 독자 개발한 것처럼 표현하지 않는다.

### 3.4 근거가 부족해 주장하지 않은 항목

- 팀원별 전체 작업 비율
- 운동별 판정 정확도
- 최소 15 FPS 또는 0.1초 지연 요구 충족 여부
- 특정 evaluator threshold의 최적성
- MediaPipe hand branch가 손목 부상 위험을 실제로 낮춘다는 효과
- 3D pose가 현재 앱에서 동작한다는 주장
- private Exercise3D dataset이 현재 2D app runtime에 필요하다는 주장

## 4. 기술 서사

### 문제

모바일 운동 피드백은 pose model 정확도만으로 끝나지 않는다. 카메라 입력, 좌표계 복원, 운동 phase 안정화, 반복 수 계산, UI state, 결과 저장이 하나의 실시간 경로로 연결되어야 한다.

### 설계 선택

- 영상 전송과 서버 추론 없이 iPhone 안에서 처리한다.
- 크로스플랫폼 제품 UI는 Flutter가, 실시간 AI runtime은 Swift/CoreML이 맡는다.
- 공통 COCO17 출력 뒤에 운동별 evaluator를 분리한다.
- 단일 프레임 임계값이 아니라 후보 상태 누적과 phase transition으로 반복을 판정한다.
- hand와 3D는 완성 기능으로 과장하지 않고 교체·확장 가능한 연구 branch로 유지한다.
- 공동 촬영한 multi-view video는 별도 pipeline에서 private 3D pseudo-label dataset으로 만들고, 공개 저장소에는 비식별 결과만 둔다.

### 현재 결과

- 캡스톤 디자인 I 결과는 현재 동작하는 1차 마일스톤이며 최종 종료 상태가 아니다.
- iOS 카메라 기반 2D pose 추론과 5개 운동 evaluator가 연결되어 있다.
- Flutter에서 목표 반복·세트 진행과 운동 결과 화면으로 이어진다.
- 사용자 인증, 기록 저장, 통계 조회는 팀의 Flutter/Firebase 계층이 담당한다.
- 사용자가 2026-08-17 Xcode에서 수동 검증 완료를 확인했다.
- 별도 dataset pipeline은 26개 sequence 중 24개를 end-to-end 처리했으며, 24개 모두 REVIEW 상태를 그대로 보존하고 FAIL 0으로 기록했다.

### 한계

- 기기별 속도와 정확도 벤치마크가 없다.
- Android AI backend가 없다.
- native path의 correct/incorrect rep, posture score, feedback history가 아직 연결되지 않았다.
- 손목 정밀 피드백과 3D temporal evaluation은 연구 단계다.
- 비디오 저장·재생, 음성 피드백, 관리자 기능 등이 남아 있다.
- dataset pipeline의 2개 sequence는 deadline snapshot에서 미완료이며 현재 앱 기능과 직접 연결되어 있지 않다.

### 한계 기반 다음 단계

1. 실제 iPhone에서 FPS, latency, frame drop, thermal 특성을 계측한다.
2. 운동별 validation clip과 기준 annotation으로 rep/phase 오류를 측정한다.
3. native evaluator의 `status`와 evidence를 correct/incorrect rep, posture score, feedback history에 연결한다.
4. projection validity와 hand confidence gate를 통과한 경우에만 손목 굽힘·회전 피드백을 활성화한다.
5. Exercise3D 결과를 pseudo-label이라는 한계를 유지한 채 3D/reference trajectory 실험에 사용한다.
6. 3D temporal stability, 개인 체형 보정, phase alignment를 검증한 뒤 app path 활성화를 판단한다.
7. iOS의 측정 기준을 확립한 뒤 Android inference backend를 구현한다.

## 5. 적용한 문서 변경

| File | 변경 |
| --- | --- |
| `README.md` | 제품 문제, 구현 범위, runtime architecture, 평가기 5종, 기여 구분, 검증, 한계, 실행법을 포함하도록 전면 재작성 |
| `plan.md` | 근거 기반 문서 작업 단계와 검토 체크리스트 추가 |
| `process.md` | 보고서·Git·코드 기반의 사실성과 기여 귀속 기록 추가 |
| `docs/migration.md` | 내부 로컬 절대 경로 제거 |

## 6. 최종 검토 기준

### 기여가 드러나는 방식

- 별도 홍보성 `My Contribution` 목록 대신 architecture와 implementation scope 안에서 구체적인 모듈로 드러냈다.
- AI research, CoreML post-processing, Swift runtime, evaluator, Flutter-native boundary를 커밋과 파일로 연결했다.
- 공동 촬영과 개인 pipeline 구현을 분리하고 `Exercise3D-Dataset-Pipeline`의 history로 보강했다.
- 팀원의 Flutter/Firebase 작업은 팀 결과로 분리했다.
- 캡스톤 I을 종료 결과가 아닌 진행 중 프로젝트의 1차 마일스톤으로 명시했다.

### 과장을 줄인 부분

- 실시간 구현을 FPS·지연 시간 충족으로 바꾸어 쓰지 않았다.
- hand overlay를 손목 정밀 피드백 완성으로 표현하지 않았다.
- 3D 연구 코드를 앱 기능으로 표현하지 않았다.
- RTMPose와 MediaPipe를 자체 모델로 표현하지 않았다.
- 자동 반복 계산을 자세 정확도 검증으로 표현하지 않았다.

### 공개 전 확인 사항

- 원본 최종 보고서는 학번 등 개인 식별 정보가 있어 저장소에 포함하지 않았다.
- README와 migration 문서에서 내부 절대 경로를 제거한다.
- 프로젝트 전체 라이선스와 bundled model 재배포 조건은 별도 검토가 필요하다.

# BPT 설치 및 실행 설명서

이 문서는 저장소를 **처음 클론한 사람** 이 아무 사전 지식 없이 앱을 빌드하고 iPhone에서 실행하기까지의 전 과정을 담고 있습니다. 위에서부터 차례대로 따라 하면 됩니다.

BPT는 스마트폰 카메라만으로 운동 자세를 실시간 분석하는 앱입니다. 카메라 영상은 기기 밖으로 나가지 않고, 모든 추론이 기기 안에서 실행됩니다.

---

## 0. 시작 전 확인

### 반드시 필요한 것

| 항목 | 이유 |
| --- | --- |
| **macOS 컴퓨터** | iOS 앱 빌드는 macOS에서만 가능합니다 |
| **Xcode** | iOS 빌드 도구. App Store에서 무료 설치 |
| **Flutter SDK** | 앱 프레임워크 |
| **iPhone 실기기** (iOS 16.0 이상) | 실시간 자세 분석에 카메라가 필요합니다 |
| **Apple ID** | 무료 계정으로 충분합니다. 유료 개발자 등록(연 $99) 불필요 |
| **USB 케이블** | iPhone과 Mac 연결용 |

### 왜 시뮬레이터로는 안 되나

iOS 시뮬레이터에는 카메라가 없습니다. 시뮬레이터에서 실행하면 로그인·화면 이동 등 UI는 확인할 수 있지만, 운동 분석 화면에서 다음 메시지가 뜨고 핵심 기능이 동작하지 않습니다.

```
Failed to configure camera: No camera device found
```

**AI 자세 분석을 확인하려면 반드시 실제 iPhone에서 실행해야 합니다.**

### 검증된 환경

아래 조합에서 처음부터 끝까지 실행해 확인했습니다. 버전이 조금 달라도 대개 동작하지만, 문제가 생기면 이 버전과 비교해 보세요.

| 도구 | 버전 |
| --- | --- |
| Flutter | 3.41.4 (stable) |
| Dart | `>=3.0.0 <4.0.0` |
| Xcode | 26.4.1 |
| CocoaPods | 1.16.2 |
| iOS Deployment Target | 16.0 |

---

## 1. 개발 도구 설치

이미 설치되어 있다면 2단계로 넘어가세요.

### 1-1. Xcode 설치

1. App Store에서 **Xcode** 를 검색해 설치합니다. (용량이 크므로 시간이 걸립니다)
2. 설치 후 Xcode를 한 번 실행해 추가 구성 요소 설치에 동의합니다.
3. 터미널에서 명령줄 도구를 연결합니다.

```sh
sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer
sudo xcodebuild -license accept
```

### 1-2. Flutter 설치

[flutter.dev/get-started](https://docs.flutter.dev/get-started/install/macos) 안내를 따르거나, Homebrew를 쓴다면:

```sh
brew install --cask flutter
```

설치 확인:

```sh
flutter --version
flutter doctor
```

`flutter doctor` 결과에서 **Flutter** 와 **Xcode** 항목에 체크 표시가 있으면 충분합니다. Android 관련 경고는 이 앱을 iOS로만 실행한다면 무시해도 됩니다.

### 1-3. CocoaPods 설치

iOS 네이티브 라이브러리(MediaPipe, Firebase)를 받아오는 도구입니다.

```sh
sudo gem install cocoapods
pod --version
```

---

## 2. 소스 내려받기

```sh
git clone https://github.com/Hanbat-Personal-Training-AI-Agent/BPT.git
cd BPT
```

> **주의**: iCloud Drive, Google Drive, Dropbox 같은 클라우드 동기화 폴더 안에서 빌드하면 코드 서명 오류가 발생할 수 있습니다. `~/Documents` 나 `~/Developer` 같은 로컬 경로에 클론하세요.

Flutter 프로젝트 루트는 **저장소 최상단** 입니다. (`pubspec.yaml` 이 있는 위치)

---

## 3. 의존성 설치

저장소 루트에서 차례대로 실행합니다.

```sh
flutter pub get
cd ios
pod install
cd ..
```

`pod install` 이 `MediaPipeTasksVision` 을 찾지 못한다는 오류를 내면, 스펙 저장소가 오래된 것이므로 갱신합니다.

```sh
cd ios
pod install --repo-update
cd ..
```

처음 실행하면 CocoaPods가 라이브러리 목록을 통째로 내려받아 몇 분 걸립니다.

### 정상 설치 확인

```sh
flutter analyze
```

`error` 가 0건이면 성공입니다. `warning` 과 `info` 는 몇 건 나와도 정상입니다.

---

## 4. Xcode 서명 설정 (가장 중요한 단계)

iOS는 서명되지 않은 앱의 설치를 허용하지 않습니다. 저장소에는 **원 개발자의 팀 ID가 그대로 들어 있어서, 다른 사람이 그대로 빌드하면 반드시 실패합니다.** 아래 설정을 본인 계정으로 바꿔야 합니다.

### 4-1. Xcode 프로젝트 열기

```sh
open ios/Runner.xcworkspace
```

> `Runner.xcodeproj` 가 아니라 **`Runner.xcworkspace`** 를 열어야 합니다. CocoaPods로 설치한 라이브러리는 workspace에만 연결되어 있어서, 프로젝트 파일을 열면 빌드가 실패합니다.

### 4-2. Apple ID 등록

1. 메뉴 막대에서 **Xcode → Settings...** (단축키 `⌘ ,`)
2. **Accounts** 탭 선택
3. 왼쪽 아래 **+** 버튼 → **Apple ID** 선택 → **Continue**
4. 본인 Apple ID와 비밀번호로 로그인

로그인하면 계정 아래에 **Personal Team** 이 생깁니다. 이것이 무료 계정용 팀이며, 이걸로 충분합니다.

### 4-3. Team과 Bundle Identifier 변경

1. 창 왼쪽 파일 목록 맨 위의 파란색 **Runner** 아이콘 클릭
2. 가운데 영역에서 **TARGETS → Runner** 선택 (PROJECT 아래가 아니라 TARGETS 아래입니다)
3. 상단 탭에서 **Signing & Capabilities** 선택
4. **Automatically manage signing** 체크박스를 켭니다
5. **Team** 드롭다운에서 방금 추가한 본인 계정의 **Personal Team** 을 선택합니다
6. **Bundle Identifier** 를 본인만의 값으로 바꿉니다

```
바꾸기 전:  com.bpt.bpt
바꾼 후:    com.본인아이디.bpt      (예: com.hongildong.bpt)
```

Bundle Identifier를 바꾸는 이유는, `com.bpt.bpt` 가 원 개발자의 팀(`U9984DX6WR`)에 이미 등록되어 있어 다른 계정으로는 서명할 수 없기 때문입니다. **세상에서 유일한 값**이어야 하므로 본인 이름이나 학번을 넣으면 됩니다.

7. 잠시 기다리면 Xcode가 프로비저닝 프로파일을 자동으로 만듭니다. **Signing Certificate** 에 본인 이름이 표시되면 성공입니다.

### 4-4. 자주 나오는 오류

| 화면에 뜨는 메시지 | 해결 |
| --- | --- |
| `No Account for Team "U9984DX6WR"` | 4-2를 안 했거나 4-3의 Team을 안 바꿨습니다 |
| `No profiles for 'com.bpt.bpt' were found` | 4-3의 6번, Bundle Identifier를 본인 값으로 바꾸세요 |
| `Failed to register bundle identifier` | 이미 누가 쓰는 이름입니다. 더 고유한 값으로 바꾸세요 |
| Team 드롭다운이 비어 있음 | 4-2의 Apple ID 로그인이 안 된 상태입니다 |

---

## 5. iPhone 준비

### 5-1. 개발자 모드 켜기

1. iPhone을 USB 케이블로 Mac에 연결합니다
2. iPhone 화면에 **"이 컴퓨터를 신뢰하시겠습니까?"** 가 뜨면 **신뢰** 를 누르고 암호를 입력합니다
3. iPhone에서 **설정 → 개인정보 보호 및 보안** 으로 들어갑니다
4. 맨 아래 **개발자 모드** 를 켭니다
5. iPhone이 재시동됩니다. 재시동 후 잠금을 풀면 확인 창이 뜨는데 **켜기** 를 누릅니다

> 개발자 모드 항목이 안 보이면, Mac에 한 번 연결한 뒤 Xcode에서 빌드를 시도하면 나타납니다.

### 5-2. 기기 인식 확인

```sh
flutter devices
```

목록에 본인 iPhone 이름이 나오면 준비 완료입니다.

---

## 6. 빌드와 실행

### 방법 A. 터미널에서 실행 (간단함)

저장소 루트에서:

```sh
flutter run --release
```

여러 기기가 연결되어 있으면 목록에서 번호를 고르라고 나옵니다.

### 방법 B. Xcode에서 실행

1. Xcode 상단 가운데의 실행 대상 선택 영역에서 본인 iPhone을 선택합니다
2. 왼쪽 위 **▶ (Run)** 버튼을 누릅니다

### 6-1. 첫 실행 시 "신뢰할 수 없는 개발자"

설치는 됐는데 앱을 누르면 열리지 않고 경고가 뜹니다. iPhone에서:

**설정 → 일반 → VPN 및 기기 관리 → (본인 Apple ID) → 신뢰**

한 번만 하면 됩니다.

### 6-2. 7일 후 앱이 실행되지 않을 때

무료 Apple ID로 서명한 앱은 **7일 뒤 만료** 됩니다. 정상 동작이며, 같은 방법으로 다시 실행하면 7일이 새로 시작됩니다. 유료 Apple Developer Program 계정은 1년입니다.

---

## 7. 앱 사용해 보기

1. 앱을 처음 열면 **카메라 권한** 을 묻습니다. 자세 분석에 필요하므로 **허용** 을 누릅니다
2. 이메일로 회원가입한 뒤 로그인합니다
3. 운동 종목을 고르고 목표 반복 수·세트 수를 정합니다
4. 종목별 **카메라 배치 안내** 를 확인하고 "확인했습니다" 를 누릅니다
5. 3·2·1 카운트다운 후 실시간 분석이 시작됩니다

### 촬영 환경

정확도가 촬영 조건에 크게 좌우됩니다.

| 항목 | 권장 |
| --- | --- |
| **거리** | 몸 전체가 화면에 **가득 차도록** |
| 각도 | 스쿼트·데드리프트·바벨로우·푸쉬업은 측면 45도, 벤치프레스는 아래쪽 시점 |
| 조명 | 사람과 배경이 구분되는 밝기 |
| 고정 | 삼각대 등으로 기기 고정 |

거리가 특히 중요합니다. 현재 파이프라인은 사람 검출기 없이 화면 전체를 한 사람의 영역으로 간주하기 때문에, 사람이 화면에서 작게 잡히면 관절 추정이 크게 흔들립니다.

---

## 8. 기능 범위

**포함**

- 이메일 회원가입·로그인, 프로필·신체 정보 관리
- 5개 종목 실시간 자세 분석 — 스쿼트, 벤치프레스, 데드리프트, 바벨로우, 푸쉬업
- 반복 횟수 자동 카운트, 세트 진행률, 실시간 자세 상태 표시
- 운동 기록 저장과 리포트·마이페이지 조회 (Cloud Firestore, 오프라인 시 로컬 캐시)

**미포함**

- **Android 실시간 AI 분석** — 앱은 Android에서도 실행되지만 운동 화면에서 "실시간 AI 카메라 코칭은 현재 iOS에서만 사용할 수 있습니다" 안내가 표시됩니다. 네이티브 추론 파이프라인이 iOS에만 구현되어 있습니다
- 음성 피드백, 운동 영상 다시보기, 관리자 대시보드

### Firebase 설정

로그인과 기록 저장은 Firebase를 사용하며, 필요한 설정은 저장소에 포함되어 있어 **추가 설정 없이 그대로 동작합니다.**

| 파일 | 용도 |
| --- | --- |
| `lib/firebase_options.dart` | Flutter에서 Firebase 초기화 (iOS 포함) |
| `android/app/google-services.json` | Android 설정 |

iOS용 `GoogleService-Info.plist` 는 없지만, 이 앱은 Dart 쪽에서 `DefaultFirebaseOptions.currentPlatform` 으로 초기화하므로 필요하지 않습니다.

본인의 Firebase 프로젝트로 바꾸려면 [FlutterFire CLI](https://firebase.google.com/docs/flutter/setup) 로 위 파일들을 다시 생성하세요.

---

## 9. 문제 해결

| 증상 | 원인과 해결 |
| --- | --- |
| `Font subsetting failed with exit code -9` | 빌드 명령에 `--no-tree-shake-icons` 를 추가하세요 |
| `MediaPipeTasksVision` 을 찾을 수 없음 | `cd ios && pod install --repo-update` |
| `Generated.xcconfig must exist` | `pod install` 전에 `flutter pub get` 을 먼저 실행하세요 |
| Xcode에서 라이브러리를 못 찾음 | `.xcodeproj` 가 아니라 `.xcworkspace` 를 열었는지 확인하세요 |
| 기기가 목록에 없음 | 개발자 모드(5-1)와 "이 컴퓨터를 신뢰" 를 확인하세요 |
| 서명 관련 오류 | 4-4 표를 확인하세요 |
| 빌드가 뒤엉킴 | `flutter clean` 후 3단계부터 다시 실행하세요 |

그래도 막히면 다음 결과를 함께 확인하세요.

```sh
flutter doctor -v
```

---

## 10. 작업 공간 정리

빌드를 반복하면 빌드 출력과 캐시가 수 GB까지 쌓입니다. 정리 스크립트가 포함되어 있습니다.

```sh
./scripts/clean_workspace.sh            # 무엇을 지울지 미리보기만
./scripts/clean_workspace.sh --apply    # 실제로 삭제
```

지우는 대상은 명령 한 줄로 되돌릴 수 있는 것들뿐이며, 항목마다 복원 방법이 함께 출력됩니다. Git이 추적하는 파일은 삭제하지 않습니다.

정리 후 다시 개발하려면:

```sh
flutter pub get
cd ios && pod install && cd ..
```

---

## 11. AI 연구 코드 (선택)

앱 실행에는 필요 없습니다. 포즈 추정 모델의 변환·검증 코드를 직접 돌려볼 때만 사용하세요.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

연구용 모델 가중치와 외부 저장소는 용량 때문에 포함하지 않았습니다. 복원 방법은 각 폴더의 안내를 참고하세요.

- [`assets/README.md`](assets/README.md) — 생성 산출물 경로
- [`models/README.md`](models/README.md) — RTMPose 가중치 복원
- [`external/README.md`](external/README.md) — 외부 저장소와 고정 리비전

파이프라인 구조 설명은 [`docs/research/rtmpose_motionagformer_image_to_pose_pipeline.md`](docs/research/rtmpose_motionagformer_image_to_pose_pipeline.md) 에 있습니다.

---

## 부록. 배포용 빌드 파일 만들기

설치 파일(`.ipa`) 형태로 전달해야 할 때 사용합니다.

```sh
flutter build ios --release --no-codesign --no-tree-shake-icons

mkdir -p dist/Payload
cp -R build/ios/iphoneos/Runner.app dist/Payload/
(cd dist && zip -qry BPT-ios-unsigned.ipa Payload && rm -rf Payload)
```

이렇게 만든 `.ipa` 는 **서명되어 있지 않아** 그대로는 설치되지 않습니다. 받는 사람이 Xcode나 사이드로딩 도구로 본인 Apple ID 서명을 해야 하므로, 가능하면 이 문서의 2~6단계대로 소스에서 직접 빌드하는 편이 확실합니다.

서명까지 포함한 `.ipa` 가 필요하면 4단계 설정을 마친 뒤:

```sh
flutter build ipa --release --no-tree-shake-icons --export-method development
```

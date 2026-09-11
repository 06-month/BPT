#!/usr/bin/env bash
# 작업 디렉터리에서 "다시 만들 수 있는" 산출물만 정리한다.
#
# 이 스크립트는 Git이 추적하는 파일을 절대 건드리지 않는다. 지우는 대상은 빌드
# 출력, 패키지 캐시, 연구용 생성물처럼 명령 한 줄로 복원되는 것들뿐이며, 복원
# 방법은 각 항목 옆에 적어 두었다.
#
#   ./scripts/clean_workspace.sh            # 무엇을 지울지 보여주기만 함 (기본)
#   ./scripts/clean_workspace.sh --apply    # 실제로 삭제
#
# 보존 대상 (이 스크립트가 건드리지 않음):
#   - Git이 추적하는 모든 파일 (소스, 앱 리소스, 문서, 번들 모델)
#   - BPT_v1.0/          제출 산출물 패키지
#   - fit3d_test.tar.gz  내려받은 데이터셋 원본
#   - 직접 촬영한 원본 영상 (assets/coreml_pipeline/videos/ 중 *_2d_3d.mp4 가 아닌 것)

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

APPLY=0
if [[ "${1:-}" == "--apply" ]]; then
  APPLY=1
elif [[ -n "${1:-}" ]]; then
  echo "사용법: $0 [--apply]" >&2
  exit 2
fi

total_kb=0

# 지울 대상 하나를 처리한다. $1=경로, $2=복원 방법 설명
consider() {
  local target="$1" restore="$2"
  [[ -e "$target" ]] || return 0
  local kb
  kb="$(du -sk "$target" 2>/dev/null | cut -f1)"
  total_kb=$((total_kb + kb))
  printf '  %-34s %8s   복원: %s\n' "$target" "$(du -sh "$target" | cut -f1)" "$restore"
  if [[ $APPLY -eq 1 ]]; then
    # 대상 안에 Git이 추적하는 파일이 섞여 있으면 통째로 지우지 않는다.
    # git clean 이 추적 파일은 남기고 나머지만 제거한다.
    if [[ -n "$(git ls-files -- "$target")" ]]; then
      git clean -fdxq -- "$target"
    else
      rm -rf "$target"
    fi
  fi
}

if [[ $APPLY -eq 1 ]]; then
  echo "== 삭제 실행 =="
else
  echo "== 미리보기 (실제 삭제하려면 --apply) =="
fi

echo
echo "[구 레이아웃 잔재]"
# 앱이 저장소 루트로 옮겨지기 전 구조의 찌꺼기. 소스는 남아 있지 않고 빌드
# 출력과 .pyc 캐시뿐이다.
consider "bpt" "없음 (구 구조 잔재, 현재 앱은 저장소 루트에 있음)"

echo
echo "[빌드 출력]"
consider "build" "flutter build"
consider "ios/Pods" "cd ios && pod install"
consider "dist" "scripts/clean_workspace.sh 주석의 IPA 패키징 절차"

echo
echo "[패키지 및 도구 캐시]"
consider ".dart_tool" "flutter pub get"
consider ".flutter-plugins-dependencies" "flutter pub get"
consider ".pytest_cache" "pytest 실행 시 자동 생성"

echo
echo "[연구용 생성물]"
consider "assets/benchmarks" "scripts/run_m0_athletepose3d_*.py 재실행"
# 이 폴더에는 직접 촬영한 원본 영상도 들어 있으므로 통째로 지우지 않고,
# 파이프라인이 만들어낸 산출물만 골라 지운다.
for sub in csv jsonl logs npz plots; do
  consider "assets/coreml_pipeline/$sub" "scripts/run_coreml_rtmpose_s_motionagformer_xs_pipeline.py 재실행"
done
while IFS= read -r rendered; do
  consider "$rendered" "위 파이프라인 스크립트의 --output-video 옵션"
done < <(find assets/coreml_pipeline/videos -name '*_2d_3d.mp4' 2>/dev/null)
consider "assets/coreml" "scripts/export_motionagformer_xs_coreml.py 재실행"
consider "assets/mediapipe" "python tools/smoke/download_pose_landmarker.py --variant lite"
consider "external" "external/README.md의 저장소·리비전 표대로 git clone"

echo
echo "[흩어진 캐시 파일]"
py_caches="$(find . -name '__pycache__' -type d -not -path './.git/*' 2>/dev/null | wc -l | tr -d ' ')"
ds_stores="$(find . -name '.DS_Store' -not -path './.git/*' 2>/dev/null | wc -l | tr -d ' ')"
printf '  %-34s %8s   복원: 자동 생성\n' "__pycache__ 디렉터리" "${py_caches}개"
printf '  %-34s %8s   복원: 불필요 (macOS 생성 파일)\n' ".DS_Store 파일" "${ds_stores}개"
if [[ $APPLY -eq 1 ]]; then
  find . -name '__pycache__' -type d -not -path './.git/*' -prune -exec rm -rf {} + 2>/dev/null || true
  find . -name '.DS_Store' -not -path './.git/*' -delete 2>/dev/null || true
fi

echo
printf '합계 약 %s\n' "$(awk -v kb="$total_kb" 'BEGIN{printf "%.1f GB", kb/1024/1024}')"

if [[ $APPLY -eq 1 ]]; then
  # 추적 파일이 하나라도 사라졌으면 즉시 되돌린다.
  missing="$(git ls-files --deleted)"
  if [[ -n "$missing" ]]; then
    echo
    echo "경고: 추적 파일이 삭제되어 복구합니다:"
    echo "$missing" | sed 's/^/  /'
    git checkout -- .
  fi

  echo
  echo "정리 완료. 개발 환경을 되돌리려면:"
  echo "  flutter pub get"
  echo "  cd ios && pod install && cd .."
else
  echo
  echo "실제로 지우려면: $0 --apply"
fi

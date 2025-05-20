import os
import json
import unicodedata


# 메타데이터(JSON) 생성
def generate_dummy_json(image_dir="dummy_images", output_path="dummy_data.json", camera_id=1):
    if not os.path.exists(image_dir):
        print(f"❌ 이미지 폴더 '{image_dir}'가 존재하지 않습니다.")
        return

    data = []
    for file_name in os.listdir(image_dir):
        if file_name.lower().endswith((".jpg", ".jpeg", ".png")):
            # 🔧 파일명 정규화
            file_name = unicodedata.normalize("NFC", file_name)
            data.append({
                "file_name": file_name,
                "camera_id": camera_id
            })

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ 생성 완료: {output_path} (총 {len(data)}개 이미지)")

if __name__ == "__main__":
    generate_dummy_json()
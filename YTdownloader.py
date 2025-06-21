import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QFileDialog, QInputDialog
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import requests
import yt_dlp
import os

class DownloadThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, ydl_opts):
        super().__init__()
        self.url = url
        self.ydl_opts = ydl_opts

    def run(self):
        import yt_dlp
        try:
            def hook(d):
                if d['status'] == 'downloading':
                    msg = d.get('filename', '')
                    if 'speed' in d and d['speed']:
                        msg += f" | 속도: {d['speed'] // 1024} KB/s"
                    if 'eta' in d and d['eta']:
                        msg += f" | 남은 시간: {d['eta']}s"
                    self.progress.emit(msg)
                elif d['status'] == 'finished':
                    self.progress.emit('다운로드 완료!')
            self.ydl_opts['progress_hooks'] = [hook]
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                ydl.download([self.url])
            self.finished.emit(True, '영상이 저장되었습니다.')
        except Exception as e:
            self.finished.emit(False, f'영상 다운로드 실패: {e}')

class ThumbnailDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('YouTube 썸네일 다운로더')
        self.setGeometry(100, 100, 400, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.url_label = QLabel('YouTube URL을 입력하세요:')
        layout.addWidget(self.url_label)
        self.url_input = QLineEdit()
        layout.addWidget(self.url_input)
        self.account_btn = QPushButton('구글 계정 연결')
        self.account_btn.clicked.connect(self.set_google_cookies)
        layout.addWidget(self.account_btn)
        self.download_btn = QPushButton('썸네일 가져오기')
        self.download_btn.clicked.connect(self.download_thumbnail)
        layout.addWidget(self.download_btn)
        self.save_btn = QPushButton('이미지 다운로드')
        self.save_btn.clicked.connect(self.save_thumbnail)
        self.save_btn.setEnabled(False)
        layout.addWidget(self.save_btn)
        self.video_btn = QPushButton('영상 다운로드')
        self.video_btn.clicked.connect(self.download_video)
        layout.addWidget(self.video_btn)
        self.status_label = QLabel('')
        layout.addWidget(self.status_label)
        self.thumbnail_label = QLabel('')
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.thumbnail_label)
        self.setLayout(layout)
        self.cookies_path = None

    def set_google_cookies(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '구글 쿠키 파일 선택', '', 'Cookies (*.txt)')
        if file_path:
            self.cookies_path = file_path
            QMessageBox.information(self, '성공', '쿠키 파일이 등록되었습니다.')
        else:
            QMessageBox.warning(self, '오류', '쿠키 파일을 선택하지 않았습니다.')

    def download_thumbnail(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, '오류', 'URL을 입력하세요.')
            return
        try:
            ydl_opts = {}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                thumbnail_url = info.get('thumbnail')
                if not thumbnail_url:
                    QMessageBox.warning(self, '오류', '썸네일을 찾을 수 없습니다.')
                    self.save_btn.setEnabled(False)
                    return
                response = requests.get(thumbnail_url)
                if response.status_code == 200:
                    with open('thumbnail.jpg', 'wb') as f:
                        f.write(response.content)
                    pixmap = QPixmap('thumbnail.jpg')
                    self.thumbnail_label.setPixmap(pixmap.scaled(320, 180, Qt.KeepAspectRatio))
                    self.save_btn.setEnabled(True)
                    self.current_thumbnail_path = 'thumbnail.jpg'
                else:
                    QMessageBox.warning(self, '오류', '썸네일 다운로드 실패.')
                    self.save_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(self, '오류', f'에러 발생: {e}')
            self.save_btn.setEnabled(False)

    def save_thumbnail(self):
        if hasattr(self, 'current_thumbnail_path') and os.path.exists(self.current_thumbnail_path):
            save_path, _ = QFileDialog.getSaveFileName(self, '이미지 저장', 'thumbnail.jpg', 'Images (*.jpg *.jpeg *.png)')
            if save_path:
                try:
                    with open(self.current_thumbnail_path, 'rb') as src, open(save_path, 'wb') as dst:
                        dst.write(src.read())
                    QMessageBox.information(self, '성공', '이미지가 저장되었습니다.')
                except Exception as e:
                    QMessageBox.critical(self, '오류', f'저장 실패: {e}')
        else:
            QMessageBox.warning(self, '오류', '저장할 썸네일이 없습니다.')

    def download_video(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, '오류', 'URL을 입력하세요.')
            return
        save_path, _ = QFileDialog.getSaveFileName(self, '영상 저장', 'video.mp4', 'Videos (*.mp4 *.mkv *.webm)')
        if not save_path:
            return
        ydl_opts = {
            'ffmpeg_location': r'C:/Users/정문21-27/ffmpeg-2025-06-17-git-ee1f79b0fa-full_build/bin',
            'outtmpl': save_path,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        }
        if self.cookies_path:
            ydl_opts['cookiefile'] = self.cookies_path
        self.status_label.setText('다운로드 시작...')
        self.video_btn.setEnabled(False)
        self.dl_thread = DownloadThread(url, ydl_opts)
        self.dl_thread.progress.connect(self.status_label.setText)
        self.dl_thread.finished.connect(self.on_download_finished)
        self.dl_thread.start()

    def on_download_finished(self, success, msg):
        self.status_label.setText(msg)
        self.video_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, '성공', msg)
        else:
            QMessageBox.critical(self, '오류', msg)

def main():
    app = QApplication(sys.argv)
    window = ThumbnailDownloader()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

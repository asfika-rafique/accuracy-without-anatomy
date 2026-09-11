# Originating environment snapshot

Read from installed package metadata on 11 September 2026 in the existing Python 3.10 project environment.
The saved run records independently record PyTorch 2.5.1+cu121 and RTX 4060 Ti.
Other versions are a current environment snapshot, not proof of their versions at every historical run.

```text
torch==2.5.1+cu121
torchvision==0.20.1+cu121
numpy==2.2.6
pyarrow==25.0.1
pillow==12.3.0
opencv-python-headless==5.0.0.93
scikit-learn==1.7.2
matplotlib==3.10.9
pandas==2.3.3
pymupdf==1.28.2
python-docx==1.2.0
huggingface_hub==1.30.0
scipy==1.15.3
```

The final manuscript was built with python-docx and exported with Microsoft Word on Windows.
Figure 2 was regenerated from unchanged summary JSON during finalization. Training was not rerun.

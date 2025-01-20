#!/bin/bash
set -e

OPENCV_VERSION="4.10.0"  # OpenCV 버전을 변수로 지정

install_opencv () {
  if [ -e "/proc/device-tree/model" ]; then
    model=$(tr -d '\0' < /proc/device-tree/model)
    echo ""
    if [[ $model == *"Orin"* ]]; then
      echo "Detecting a Jetson Nano Orin."
      # Use always "-j 4"
      NO_JOB=4
      ARCH=8.7
      PTX="sm_87"
    else
      echo "Unable to determine the Jetson Orin model."
      exit 1
    fi
    echo ""
  else
    echo "Error: /proc/device-tree/model not found. Are you sure this is a Jetson Orin?"
    exit 1
  fi
  echo "Installing OpenCV $OPENCV_VERSION on your Orin"
  echo "It will take several hours!"
  cd ~
  sudo sh -c "echo '/usr/local/cuda/lib64' >> /etc/ld.so.conf.d/nvidia-tegra.conf"
  sudo ldconfig
  if [ -f /etc/os-release ]; then
      . /etc/os-release
      VERSION_MAJOR=$(echo "$VERSION_ID" | cut -d'.' -f1)
      if [ "$VERSION_MAJOR" = "22" ]; then
        sudo apt-get install -y libswresample-dev libdc1394-dev
      else
        sudo apt-get install -y libavresample-dev libdc1394-22-dev
      fi
  else
    sudo apt-get install -y libavresample-dev libdc1394-22-dev
  fi

  sudo apt-get install -y gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav
  sudo apt-get install -y cmake
  sudo apt-get install -y libjpeg-dev libjpeg8-dev libjpeg-turbo8-dev
  sudo apt-get install -y libpng-dev libtiff-dev libglew-dev
  sudo apt-get install -y libavcodec-dev libavformat-dev libswscale-dev
  sudo apt-get install -y libgtk2.0-dev libgtk-3-dev libcanberra-gtk*
  sudo apt-get install -y python3-pip
  sudo apt-get install -y libxvidcore-dev libx264-dev
  sudo apt-get install -y libtbb-dev libxine2-dev
  sudo apt-get install -y libv4l-dev v4l-utils qv4l2
  sudo apt-get install -y libtesseract-dev libpostproc-dev
  sudo apt-get install -y libvorbis-dev
  sudo apt-get install -y libfaac-dev libmp3lame-dev libtheora-dev
  sudo apt-get install -y libopencore-amrnb-dev libopencore-amrwb-dev
  sudo apt-get install -y libopenblas-dev libatlas-base-dev libblas-dev
  sudo apt-get install -y liblapack-dev liblapacke-dev libeigen3-dev gfortran
  sudo apt-get install -y libhdf5-dev libprotobuf-dev protobuf-compiler
  sudo apt-get install -y libgoogle-glog-dev libgflags-dev
  cd ~
  sudo rm -rf opencv*    

  # Download and unzip OpenCV and OpenCV contrib using wget
  wget -O opencv.zip https://github.com/opencv/opencv/archive/${OPENCV_VERSION}.zip 
  wget -O opencv_contrib.zip https://github.com/opencv/opencv_contrib/archive/${OPENCV_VERSION}.zip
  
  unzip opencv.zip
  unzip opencv_contrib.zip
  
  mv opencv-${OPENCV_VERSION} opencv
  mv opencv_contrib-${OPENCV_VERSION} opencv_contrib
  
  cd ~/opencv
  mkdir build
  cd build
  cmake -D CMAKE_BUILD_TYPE=RELEASE \
  -D CMAKE_INSTALL_PREFIX=/usr \
  -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib/modules \
  -D EIGEN_INCLUDE_PATH=/usr/include/eigen3 \
  -D WITH_OPENCL=OFF \
  -D CUDA_ARCH_BIN=${ARCH} \
  -D CUDA_ARCH_PTX=${PTX} \
  -D WITH_CUDA=ON \
  -D WITH_CUDNN=ON \
  -D WITH_CUBLAS=ON \
  -D ENABLE_FAST_MATH=ON \
  -D CUDA_FAST_MATH=ON \
  -D OPENCV_DNN_CUDA=ON \
  -D ENABLE_NEON=ON \
  -D WITH_QT=OFF \
  -D WITH_OPENMP=ON \
  -D BUILD_TIFF=ON \
  -D WITH_FFMPEG=ON \
  -D WITH_GSTREAMER=ON \
  -D WITH_TBB=ON \
  -D BUILD_TBB=ON \
  -D BUILD_TESTS=OFF \
  -D WITH_EIGEN=ON \
  -D WITH_V4L=ON \
  -D WITH_LIBV4L=ON \
  -D WITH_PROTOBUF=ON \
  -D OPENCV_ENABLE_NONFREE=ON \
  -D INSTALL_C_EXAMPLES=OFF \
  -D INSTALL_PYTHON_EXAMPLES=OFF \
  -D PYTHON3_PACKAGES_PATH=/usr/lib/python3/dist-packages \
  -D OPENCV_GENERATE_PKGCONFIG=ON \
  -D BUILD_EXAMPLES=OFF \
  -D CMAKE_CXX_FLAGS="-march=native -mtune=native" \
  -D CMAKE_C_FLAGS="-march=native -mtune=native" ..
  make -j ${NO_JOB}  
  directory="/usr/include/opencv4/opencv2"
  if [ -d "$directory" ]; then
    sudo rm -rf "$directory"
  fi    
  sudo make install
  sudo ldconfig
  make clean
  sudo apt-get update    
  echo "Congratulations!"
  echo "You've successfully installed OpenCV $OPENCV_VERSION on your Orin"
}

# OpenCV 버전 확인 함수
check_opencv_version () {
  version=$(python3 -c "import cv2; print(cv2.__version__)" 2>/dev/null || echo "not installed")
  echo $version
}

cd ~
opencv_version=$(check_opencv_version)
if [[ "$opencv_version" != "$OPENCV_VERSION" ]]; then
  echo "현재 설치된 OpenCV 버전: $opencv_version"
  echo "OpenCV $OPENCV_VERSION을 설치합니다."
  install_opencv
else
  echo "OpenCV $OPENCV_VERSION이 이미 설치되어 있습니다."
fi

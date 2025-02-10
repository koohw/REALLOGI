import React, { useEffect } from "react";
import { useDispatch } from "react-redux";
import { persistor } from "../store";
import { useAuth } from "../hooks/useAuth";

const SessionCleanupHandler = ({ children }) => {
  const dispatch = useDispatch();
  const { logout } = useAuth();

  useEffect(() => {
    const handleWindowClose = async (event) => {
      event.preventDefault();

      try {
        // 로그아웃 처리
        await logout();

        // Redux 상태 초기화
        await persistor.purge();

        // localStorage 정리
        localStorage.removeItem("persist:user");

        // 세션스토리지 정리 (필요한 경우)
        sessionStorage.clear();

        // 추가적인 쿠키 정리
        document.cookie.split(";").forEach((c) => {
          document.cookie = c
            .replace(/^ +/, "")
            .replace(
              /=.*/,
              "=;expires=" + new Date().toUTCString() + ";path=/"
            );
        });
      } catch (error) {
        console.error("Cleanup failed:", error);
      }

      // Chrome 브라우저 대응
      event.returnValue = "";
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        // 브라우저 탭이 백그라운드로 갈 때도 정리 수행
        handleWindowClose({ preventDefault: () => {} });
      }
    };

    window.addEventListener("beforeunload", handleWindowClose);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("beforeunload", handleWindowClose);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [logout, dispatch]);

  return <>{children}</>;
};

export default SessionCleanupHandler;

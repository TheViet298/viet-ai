# Môi trường HTTPS GPS cục bộ

Profile này dành cho kiểm thử trên Linux, không phải cấu hình production. Không dùng DB hay tài khoản thật. TLS certificate phải được máy/browser kiểm thử tin cậy; `curl -k` chỉ kiểm tra transport, không chứng minh browser cấp quyền vị trí.

## Khởi chạy

1. Cài dependency frontend bằng `npm --prefix frontend ci`. Cài browser bằng `cd frontend && npx playwright install chromium firefox` nếu cần E2E.
2. Chạy ở hai terminal: `GPS_E2E_ACCESS_LOG=1 python3 scripts/gps-e2e-server.py backend > /tmp/gps-https-backend.log 2>&1` và `python3 scripts/gps-e2e-server.py frontend`. Backend dùng DB tạm và tắt LLM/tracing; frontend dùng `.next-gps-e2e`, `tsconfig.e2e.json` và cổng 13000. Dừng bằng Ctrl-C để teardown.
3. Chuẩn bị thư mục ngoài repository chứa `cert.pem` và `key.pem`, với SAN khớp hostname/IP máy kiểm thử. Có thể dùng CA thử nghiệm được máy/browser tin cậy. Không commit private key.
4. Đặt `GPS_TLS_DIR` tới thư mục certificate và `GPS_PROXY_LOG_DIR` tới thư mục log tạm rỗng. Chạy `docker compose -f docker-compose.gps-https.yml up`.
5. Truy cập `https://<hostname-trong-certificate>:8443/chat`. Auth, GPS và worker dùng cùng origin; raster tile provider phải dùng HTTPS và có attribution.
6. Dừng proxy bằng `docker compose -f docker-compose.gps-https.yml down`, rồi dừng hai server. Không dùng profile này đồng thời với Playwright đang tự quản lý cùng các cổng.

## Cấu hình API

Browser mặc định gửi `/api/v1/...` cùng origin. `API_PROXY_TARGET` chỉ dùng phía Next.js để rewrite tới backend; trong Docker Compose chính là `http://backend:8000`. `NEXT_PUBLIC_API_URL` là override build-time cho môi trường chủ động dùng API khác origin; khi kiểm thử HTTPS nên để trống. Không đặt backend hostname của Docker vào biến public.

## Privacy và kiểm chứng

Proxy chỉ ghi method, path không query, status và số byte. Nginx error log bị tắt trong profile thử nghiệm vì lỗi upstream có thể ghi nguyên URI. Middleware backend xóa query nearby khỏi scope trước access log; test bao phủ 200/422/503. Không cấu hình tracing trong môi trường thử nghiệm này.

Dùng tọa độ giả lập dễ nhận diện, thử response thành công và query lỗi validation, rồi tìm hai giá trị trong **toàn bộ** log proxy/backend. Khi upstream dừng, thử 502 và kiểm tra lại log. Không đưa tọa độ thật vào báo cáo/ảnh/log. Kết quả chỉ chứng minh các lớp log đã kiểm tra; proxy/tracing bên ngoài profile cần audit riêng.

Probe có thể chạy lại, dùng CA/certificate thử nghiệm được truyền rõ ràng:

```bash
python3 scripts/check-gps-https.py --ca "$GPS_TLS_DIR/cert.pem" --log-dir "$GPS_PROXY_LOG_DIR" --backend-log /tmp/gps-https-backend.log
```

Probe kiểm tra nearby 200/422, redirect dấu `/`, trang chat, worker, đăng ký/đăng nhập giả lập và scan log. Sau khi dừng backend, chạy lại cùng lệnh với `--expect-upstream-down` để kiểm tra 502. Không chạy probe vào môi trường thật; probe tạo tài khoản giả trong DB tạm. Browser còn phải tin cậy certificate riêng; trust của probe không thay đổi trust của hệ điều hành.

Để kiểm tra browser: đăng nhập bằng tài khoản giả tạo mới, chia sẻ GPS, chuyển nhập tay, dừng chia sẻ, reload, kiểm tra worker/map/directions; kiểm tra DevTools không có mixed content. Kiểm thử hộp thoại Allow/Block thật và GPS phần cứng phải ghi riêng theo OS/browser.

Nguồn cấu hình: [Nginx log module](https://nginx.org/en/docs/http/ngx_http_log_module.html), [Next.js 14 rewrites](https://nextjs.org/docs/14/app/api-reference/next-config-js/rewrites).

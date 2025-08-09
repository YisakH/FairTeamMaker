// debug_server.js
const http = require('http');

const port = 3000;
const host = '0.0.0.0';

const server = http.createServer((req, res) => {
    console.log(`\n--- New Request Received ---`);
    console.log(`Timestamp: ${new Date().toISOString()}`);
    console.log(`URL: ${req.url}`);
    console.log('Headers:');
    // 헤더를 예쁘게 출력합니다.
    console.log(JSON.stringify(req.headers, null, 2));

    // 브라우저에도 헤더 정보를 보여줍니다.
    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({
        message: 'Nginx가 보낸 헤더 정보를 아래와 같이 확인했습니다. 터미널의 로그를 확인하세요.',
        receivedHeaders: req.headers
    }));
});

server.listen(port, host, () => {
    console.log(`Header-Checking-Server is listening on http://${host}:${port}`);
    console.log('Now, access https://maketeam.2esak.com from your browser.');
});

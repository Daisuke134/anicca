import Foundation

final class TestURLProtocol: URLProtocol {
    static var requestHandler: ((URLRequest) throws -> (URLResponse, Data))?
    static var interceptedURL: URL?
    static var observedRequestURLs: [String] = []

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        Self.observedRequestURLs.append(request.url?.absoluteString ?? "<nil>")
        if let interceptedURL = Self.interceptedURL,
           !(request.url?.path.hasSuffix(interceptedURL.path) ?? false) {
            client?.urlProtocol(self, didFailWithError: URLError(.cancelled))
            return
        }

        guard let handler = Self.requestHandler else {
            fatalError("TestURLProtocol.requestHandler not set")
        }
        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

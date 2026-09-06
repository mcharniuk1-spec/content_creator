// Optional macOS local OCR. Source pixels remain on the device.
import Foundation
import Vision

guard CommandLine.arguments.count == 2 else { exit(2) }
do {
    let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
    guard data.count <= 65536,
          let files = try JSONSerialization.jsonObject(with: data) as? [String],
          files.count <= 48 else { exit(2) }
    for (index, path) in files.enumerated() {
        try autoreleasepool {
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = false
            request.automaticallyDetectsLanguage = true
            request.usesCPUOnly = true
            let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path), options: [:])
            do {
                try handler.perform([request])
                let observations = (request.results ?? []).prefix(200).compactMap { item -> [String: Any]? in
                    guard let text = item.topCandidates(1).first else { return nil }
                    let box = item.boundingBox
                    return ["text": String(text.string.prefix(2000)), "confidence": text.confidence,
                            "bbox_normalized_bottom_left": [box.origin.x, box.origin.y, box.width, box.height]]
                }
                let output: [String: Any] = ["index": index, "state": "OBSERVED", "observations": observations,
                                            "observation_limit": 200, "revision": request.revision]
                let payload = try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys])
                print(String(decoding: payload, as: UTF8.self))
            } catch {
                print("{\"index\":\(index),\"state\":\"OCR_FAILED\",\"error\":\"VISION_REQUEST_FAILED\"}")
            }
        }
    }
} catch {
    exit(2)
}

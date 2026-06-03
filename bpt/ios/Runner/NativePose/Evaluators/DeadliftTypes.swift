import Foundation

enum DeadliftStatus: String {
    case idle
    case bottom
    case rising
    case top
    case lowering
    case unknown
}

struct DeadliftFrameResult {
    let frameIndex: Int
    let status: DeadliftStatus
    let rawStatusCandidate: DeadliftStatus?
    let candidateStatus: DeadliftStatus?
    let candidateStatusCount: Int
    let statusFrameCount: Int
    let rep: Int
    let done: Bool
    let source: String
    let motion3DAvailable: Bool
    let liftProgressNorm: Double?
    let liftDepthDeltaNorm: Double?
    let hipYVelocity: Double?
    let hipCenterY: Double?
    let bottomHipYBaseline: Double?
    let legLength: Double?
    let leftHipAngleDegrees: Double?
    let rightHipAngleDegrees: Double?
    let avgHipAngleDegrees: Double?
    let leftKneeAngleDegrees: Double?
    let rightKneeAngleDegrees: Double?
    let avgKneeAngleDegrees: Double?
    let torsoLeanAngleDegrees: Double?
    let torsoLeanDeltaDegrees: Double?
    let shoulderHeightNorm: Double?
    let shoulderHeightDeltaNorm: Double?
    let loweringTrigger: String
    let currentRepMaxLiftDepthNorm: Double?
    let currentRepMaxHipAngleDegrees: Double?
    let currentRepMaxKneeAngleDegrees: Double?
    let repStarted: Bool
    let sawRising: Bool
    let reachedTop: Bool
    let sawLowering: Bool
    let lastCompletedRepSummary: DeadliftRepSummary?

    // New arm/bar proxy & bottom detection fields
    let armBarProxyYNorm: Double?
    let armBarProxyDelta1: Double?
    let armBarProxyVelocityWindow: Double?
    let bottomArmProxyBaseline: Double?
    let armProxyNearBottom: Bool
    let hipNearBottom: Bool
    let strictProgressBottom: Bool
    let loweringTriggerReason: String
    let bottomTriggerReason: String
    let progressDropFromTop: Double?
    let progressDroppedEnoughFromTop: Bool
    let elapsedLoweringFrames: Int
    let elapsedLoweringFramesEnough: Bool
    let loweringToBottomConfirmationFrames: Int
    let topProgressNorm: Double?
    let topArmProxyYNorm: Double?
    let armBarProxyDropFromTop: Double?
    let framesSinceTop: Int
    let realDescentAfterTop: Bool
    let shouldCompleteRepAtBottom: Bool
    let wristProxyY: Double?
    let wristLowerShinY: Double?
    let wristBelowLowerShin: Bool
    let elbowProxyY: Double?
    let elbowAboveWaist: Bool

    var liftDepthNorm: Double? { liftProgressNorm }
    var sawLifting: Bool { sawRising }

    var dictionary: [String: Any] {
        [
            "frame_index": frameIndex,
            "status": status.rawValue,
            "raw_status_candidate": rawStatusCandidate.map { $0.rawValue as Any } ?? NSNull(),
            "candidate_status": candidateStatus.map { $0.rawValue as Any } ?? NSNull(),
            "candidate_status_count": candidateStatusCount,
            "status_frame_count": statusFrameCount,
            "rep": rep,
            "done": done,
            "source": source,
            "motion3d_available": motion3DAvailable,
            "lift_progress_norm": jsonValue(liftProgressNorm),
            "lift_depth_norm": jsonValue(liftProgressNorm),
            "lift_depth_delta_norm": jsonValue(liftDepthDeltaNorm),
            "hip_y_velocity": jsonValue(hipYVelocity),
            "hip_center_y": jsonValue(hipCenterY),
            "bottom_hip_y_baseline": jsonValue(bottomHipYBaseline),
            "leg_length": jsonValue(legLength),
            "left_hip_angle_degrees": jsonValue(leftHipAngleDegrees),
            "right_hip_angle_degrees": jsonValue(rightHipAngleDegrees),
            "avg_hip_angle_degrees": jsonValue(avgHipAngleDegrees),
            "left_knee_angle_degrees": jsonValue(leftKneeAngleDegrees),
            "right_knee_angle_degrees": jsonValue(rightKneeAngleDegrees),
            "avg_knee_angle_degrees": jsonValue(avgKneeAngleDegrees),
            "torso_lean_angle_degrees": jsonValue(torsoLeanAngleDegrees),
            "torso_lean_delta_degrees": jsonValue(torsoLeanDeltaDegrees),
            "shoulder_height_norm": jsonValue(shoulderHeightNorm),
            "shoulder_height_delta_norm": jsonValue(shoulderHeightDeltaNorm),
            "lowering_trigger": loweringTrigger,
            "current_rep_max_lift_depth_norm": jsonValue(currentRepMaxLiftDepthNorm),
            "current_rep_max_hip_angle_degrees": jsonValue(currentRepMaxHipAngleDegrees),
            "current_rep_max_knee_angle_degrees": jsonValue(currentRepMaxKneeAngleDegrees),
            "rep_started": repStarted,
            "saw_rising": sawRising,
            "reached_top": reachedTop,
            "saw_lowering": sawLowering,
            "last_completed_rep_summary": lastCompletedRepSummary.map { $0.dictionary as Any } ?? NSNull(),
            
            // New arm/bar proxy & bottom detection fields
            "arm_bar_proxy_y_norm": jsonValue(armBarProxyYNorm),
            "arm_bar_proxy_delta1": jsonValue(armBarProxyDelta1),
            "arm_bar_proxy_velocity_window": jsonValue(armBarProxyVelocityWindow),
            "bottom_arm_proxy_baseline": jsonValue(bottomArmProxyBaseline),
            "arm_proxy_near_bottom": armProxyNearBottom,
            "hip_near_bottom": hipNearBottom,
            "strict_progress_bottom": strictProgressBottom,
            "lowering_trigger_reason": loweringTriggerReason,
            "bottom_trigger_reason": bottomTriggerReason,
            "progress_drop_from_top": jsonValue(progressDropFromTop),
            "progress_dropped_enough_from_top": progressDroppedEnoughFromTop,
            "elapsed_lowering_frames": elapsedLoweringFrames,
            "elapsed_lowering_frames_enough": elapsedLoweringFramesEnough,
            "lowering_to_bottom_confirmation_frames": loweringToBottomConfirmationFrames,
            "top_progress_norm": jsonValue(topProgressNorm),
            "top_arm_proxy_y_norm": jsonValue(topArmProxyYNorm),
            "arm_bar_proxy_drop_from_top": jsonValue(armBarProxyDropFromTop),
            "frames_since_top": framesSinceTop,
            "real_descent_after_top": realDescentAfterTop,
            "should_complete_rep_at_bottom": shouldCompleteRepAtBottom,
            "wrist_proxy_y": jsonValue(wristProxyY),
            "wrist_lower_shin_y": jsonValue(wristLowerShinY),
            "wrist_below_lower_shin": wristBelowLowerShin,
            "elbow_proxy_y": jsonValue(elbowProxyY),
            "elbow_above_waist": elbowAboveWaist,
        ]
    }

    private func jsonValue(_ value: Double?) -> Any {
        value.map { $0 as Any } ?? NSNull()
    }
}

struct DeadliftRepSummary {
    let repIndex: Int
    let startFrame: Int
    let topFrame: Int?
    let endFrame: Int?
    let maxLiftDepthNorm: Double
    let maxHipAngleDegrees: Double?
    let maxKneeAngleDegrees: Double?
    let warnings: [String]

    var dictionary: [String: Any] {
        [
            "rep_index": repIndex,
            "start_frame": startFrame,
            "top_frame": topFrame.map { $0 as Any } ?? NSNull(),
            "end_frame": endFrame.map { $0 as Any } ?? NSNull(),
            "max_lift_depth_norm": maxLiftDepthNorm,
            "max_hip_angle_degrees": maxHipAngleDegrees.map { $0 as Any } ?? NSNull(),
            "max_knee_angle_degrees": maxKneeAngleDegrees.map { $0 as Any } ?? NSNull(),
            "warnings": warnings,
        ]
    }
}

struct DeadliftSessionSummary {
    let completedRepCount: Int
    let repCount: Int
    let avgMaxLiftDepthNorm: Double?
    let maxLiftDepthNorm: Double?
    let maxHipAngleDegrees: Double?
    let maxKneeAngleDegrees: Double?

    var dictionary: [String: Any] {
        [
            "completed_rep_count": completedRepCount,
            "rep_count": repCount,
            "avg_max_lift_depth_norm": avgMaxLiftDepthNorm.map { $0 as Any } ?? NSNull(),
            "max_lift_depth_norm": maxLiftDepthNorm.map { $0 as Any } ?? NSNull(),
            "max_hip_angle_degrees": maxHipAngleDegrees.map { $0 as Any } ?? NSNull(),
            "max_knee_angle_degrees": maxKneeAngleDegrees.map { $0 as Any } ?? NSNull(),
        ]
    }
}

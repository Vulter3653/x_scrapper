# replicate_wendys_h1_h2_h3_in_R.R
#
# 목적: wendys_h1_h2_h3_r_replication_dataset.csv 하나로
#       H1, H2, H3 최종 모형을 R에서 재현한다.
#
# 사용법:
#   df <- read.csv("20260615wendy's/data/wendys_h1_h2_h3_r_replication_dataset.csv",
#                  stringsAsFactors = FALSE, na.strings = "NA")
#   source("20260615wendy's/code/replicate_wendys_h1_h2_h3_in_R.R")
#
# 주의:
#   - R의 factor() 기준 범주는 최솟값(숫자형) 또는 알파벳 첫 순서(문자형)가 기본이다.
#     Python/statsmodels drop_first=True와 동일 방식이므로 focal coefficient는
#     동일하게 재현되어야 한다. 절편과 FE dummy 계수는 다를 수 있다.
#   - H2: h2_aggressive_model_dummy / h2_aggressive_human_dummy는 non_humor 행에서 NA.
#     반드시 subset()으로 해당 sample을 제한한 뒤 사용한다.
#   - H3: h3_analysis_flag == 1인 960개 행만 사용 (quarter_total_posts >= 10).
#
# 예상 결과 (Python 분석 기준):
#   H1 binary  : pred_humor_final_050         β ≈  0.2918, p ≈ 0.0088
#   H1 prob    : p_humor_final_tfidf_logreg   β ≈  0.8404, p ≈ 0.0175
#   H1 human   : final_humor_binary           β ≈  0.3171, p ≈ 0.0307
#   H2 model   : h2_aggressive_model_dummy    β ≈  0.4056, p ≈ 0.0060
#   H2 human   : h2_aggressive_human_dummy    β ≈  0.6405, p ≈ 0.0010
#   H3-pre β1  : humor_proportion_quarter_loo β ≈ -6.3289, p ≈ 0.0103
#   H3-pre β2  : ..._sq                       β ≈ +4.3189, p ≈ 0.0395 (U자형; H3 기각)
#   H3-main β1 : aggressive...loo             β ≈ -1.9777, p ≈ 0.5532
#   H3-main β2 : aggressive..._sq             β ≈ -3.2814, p ≈ 0.6929 (not_support; H3 기각)
#   H3-other β2: other..._sq                  β ≈ +7.8688, p ≈ 0.0047 (U자형; H3 기각)
#   H3-joint agg β1 ≈ -2.3560; agg β2 ≈ -3.7276
#   H3-joint oth γ1 ≈ -7.7528; oth γ2 ≈ +8.1417

# ── 헬퍼 함수 ────────────────────────────────────────────────────────────────

print_focal <- function(model, focal_var, model_label) {
  coefs <- summary(model)$coefficients
  if (focal_var %in% rownames(coefs)) {
    b <- coefs[focal_var, "Estimate"]
    p <- coefs[focal_var, "Pr(>|t|)"]
    n_obs <- nobs(model)
    cat(sprintf(
      "[%s] %s: beta=%.4f, p=%.4f, n=%d\n",
      model_label, focal_var, b, p, n_obs
    ))
  } else {
    cat(sprintf("[%s] '%s' 계수를 찾을 수 없음. rownames 확인 필요.\n",
                model_label, focal_var))
    print(rownames(coefs))
  }
}

# 데이터 로드 (이 스크립트 외부에서 df를 이미 로드했다면 건너뜀)
if (!exists("df")) {
  stop(paste(
    "df가 정의되지 않았습니다.",
    "먼저 다음 코드를 실행하세요:",
    "df <- read.csv(\"20260615wendy's/data/wendys_h1_h2_h3_r_replication_dataset.csv\",",
    "               stringsAsFactors = FALSE, na.strings = \"NA\")"
  ))
}

cat("=== 데이터 확인 ===\n")
cat(sprintf("  rows: %d, cols: %d\n", nrow(df), ncol(df)))
cat(sprintf("  h1_full_sample_flag 합계: %d (기대: 978)\n", sum(df$h1_full_sample_flag, na.rm = TRUE)))
cat(sprintf("  h1_human_validation_flag 합계: %d (기대: 597)\n", sum(df$h1_human_validation_flag, na.rm = TRUE)))
cat(sprintf("  h2_model_humor_only_flag 합계: %d (기대: 564)\n", sum(df$h2_model_humor_only_flag, na.rm = TRUE)))
cat(sprintf("  h2_human_validation_flag 합계: %d (기대: 278)\n", sum(df$h2_human_validation_flag, na.rm = TRUE)))
cat(sprintf("  h3_analysis_flag 합계: %d (기대: 960)\n", sum(df$h3_analysis_flag, na.rm = TRUE)))
cat("\n")

# ── H1: 유머 vs. 비유머 참여도 차이 ─────────────────────────────────────────
cat("=================================================================\n")
cat("H1: 유머 vs. 비유머 (최종 모형: time FE + text + hashtag + mention)\n")
cat("=================================================================\n")

# H1 Binary — full sample (n=978)
h1_binary <- lm(
  log1p_engagement_total ~ pred_humor_final_050 +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h1_full_sample_flag == 1)
)
print_focal(h1_binary, "pred_humor_final_050", "H1_binary_M7")
# 기대: β ≈ 0.2918, p ≈ 0.0088

# H1 Probability — full sample (n=978)
h1_prob <- lm(
  log1p_engagement_total ~ p_humor_final_tfidf_logreg +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h1_full_sample_flag == 1)
)
print_focal(h1_prob, "p_humor_final_tfidf_logreg", "H1_probability_M7")
# 기대: β ≈ 0.8404, p ≈ 0.0175

# H1 Human Validation (n=597)
h1_human <- lm(
  log1p_engagement_total ~ final_humor_binary +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h1_human_validation_flag == 1)
)
print_focal(h1_human, "final_humor_binary", "H1_human_M7")
# 기대: β ≈ 0.3171, p ≈ 0.0307

cat("\n")

# ── H2: 공격적 유머 vs. 기타 유머 참여도 차이 ─────────────────────────────
cat("=================================================================\n")
cat("H2: 공격적 유머 vs. 기타 유머 (유머 게시물 only)\n")
cat("=================================================================\n")

# H2 Model-based (n=564: aggressive=200, other_humor=364)
h2_model <- lm(
  log1p_engagement_total ~ h2_aggressive_model_dummy +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h2_model_humor_only_flag == 1)
)
print_focal(h2_model, "h2_aggressive_model_dummy", "H2_model_M7")
# 기대: β ≈ 0.4056, p ≈ 0.0060

# H2 Human Validation (n=278: aggressive=95, other_humor=183)
h2_human <- lm(
  log1p_engagement_total ~ h2_aggressive_human_dummy +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h2_human_validation_flag == 1)
)
print_focal(h2_human, "h2_aggressive_human_dummy", "H2_human_M7")
# 기대: β ≈ 0.6405, p ≈ 0.0010

cat("\n")

# ── H3: 유머 강도와 참여도의 역 U자형 관계 ───────────────────────────────
cat("=================================================================\n")
cat("H3: 유머 사용 강도와 참여도 역 U자형 검증 (n=960, quarter>=10)\n")
cat("주의: year_quarter FE 사용 금지 (LOO 변수와 같은 수준)\n")
cat("=================================================================\n")

# H3-pre: 전체 유머 비율 (n=960)
h3_pre <- lm(
  log1p_engagement_total ~
    humor_proportion_quarter_loo +
    humor_proportion_quarter_loo_sq +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h3_analysis_flag == 1)
)
print_focal(h3_pre, "humor_proportion_quarter_loo",    "H3_pre_M7_beta1")
print_focal(h3_pre, "humor_proportion_quarter_loo_sq", "H3_pre_M7_beta2")
# 기대: β1 ≈ -6.3289 (p≈0.0103), β2 ≈ +4.3189 (p≈0.0395)
# 해석: β2>0 → U자형 (역 U자형 아님) → H3 기각

# H3-main: 공격적 유머 비율 (n=960)
h3_main <- lm(
  log1p_engagement_total ~
    aggressive_humor_proportion_quarter_loo +
    aggressive_humor_proportion_quarter_loo_sq +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h3_analysis_flag == 1)
)
print_focal(h3_main, "aggressive_humor_proportion_quarter_loo",    "H3_main_M7_beta1")
print_focal(h3_main, "aggressive_humor_proportion_quarter_loo_sq", "H3_main_M7_beta2")
# 기대: β1 ≈ -1.9777 (p≈0.5532), β2 ≈ -3.2814 (p≈0.6929)
# 해석: β2 불유의 → not_support → H3 기각

# H3-supplemental: 기타 유머 비율 (n=960)
h3_other <- lm(
  log1p_engagement_total ~
    other_humor_proportion_quarter_loo +
    other_humor_proportion_quarter_loo_sq +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h3_analysis_flag == 1)
)
print_focal(h3_other, "other_humor_proportion_quarter_loo",    "H3_other_M8_beta1")
print_focal(h3_other, "other_humor_proportion_quarter_loo_sq", "H3_other_M8_beta2")
# 기대: β1 ≈ -6.8614 (p≈0.0043), β2 ≈ +7.8688 (p≈0.0047)
# 해석: β2>0 → U자형 (역 U자형 아님) → H3 기각

# H3-joint: 공격적 유머 + 기타 유머 동시 투입 (마스킹 검증)
h3_joint <- lm(
  log1p_engagement_total ~
    aggressive_humor_proportion_quarter_loo +
    aggressive_humor_proportion_quarter_loo_sq +
    other_humor_proportion_quarter_loo +
    other_humor_proportion_quarter_loo_sq +
    factor(created_year) + factor(created_month) + factor(created_hour) +
    text_length + hashtag_count + mention_count,
  data = subset(df, h3_analysis_flag == 1)
)
print_focal(h3_joint, "aggressive_humor_proportion_quarter_loo",    "H3_joint_M2_agg_beta1")
print_focal(h3_joint, "aggressive_humor_proportion_quarter_loo_sq", "H3_joint_M2_agg_beta2")
print_focal(h3_joint, "other_humor_proportion_quarter_loo",         "H3_joint_M2_oth_gamma1")
print_focal(h3_joint, "other_humor_proportion_quarter_loo_sq",      "H3_joint_M2_oth_gamma2")
# 기대: agg β1 ≈ -2.3560, β2 ≈ -3.7276; oth γ1 ≈ -7.7528, γ2 ≈ +8.1417
# 해석: agg → not_support; oth → U_shape; 마스킹 없음 확인

cat("\n")
cat("=================================================================\n")
cat("전체 모형 실행 완료\n")
cat("focal coefficient가 기대값과 크게 다를 경우 다음을 확인하세요:\n")
cat("  1. subset 조건 (h1/h2/h3 sample flag)\n")
cat("  2. na.strings='NA' 옵션으로 로드했는지\n")
cat("  3. year_quarter FE를 모형에 포함하지 않았는지 (H3)\n")
cat("  4. squared term이 proportion의 제곱인지 (loo^2)\n")
cat("=================================================================\n")

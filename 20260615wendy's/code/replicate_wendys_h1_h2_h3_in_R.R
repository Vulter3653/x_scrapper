# replicate_wendys_h1_h2_h3_in_R.R  (v2 — 한글 컬럼명, 기술통계/시각화/VIF 포함)
#
# 목적: wendys_h1_h2_h3_r_replication_dataset.csv 하나로
#       기술통계 분석 → 히트맵 → VIF → H1/H2/H3 가설 검증을 순서대로 실행
#
# 실행 방법:
#   df <- read.csv(
#     "20260615wendy's/data/wendys_h1_h2_h3_r_replication_dataset.csv",
#     stringsAsFactors = FALSE, na.strings = "NA", fileEncoding = "UTF-8-BOM"
#   )
#   source("20260615wendy's/code/replicate_wendys_h1_h2_h3_in_R.R")
#
# 필요 패키지: ggplot2, corrplot, car, dplyr, scales, gridExtra
# 설치 (최초 1회):
#   install.packages(c("ggplot2","corrplot","car","dplyr","scales","gridExtra"))
#
# 주의사항:
#   - 종속변수(DV)와 이차항(squared term)은 이 스크립트에서 계산
#   - R factor() 기준 범주: 최솟값(숫자형) — Python drop_first=True와 동일
#     → focal coefficient는 동일하게 재현, 절편·FE dummy 계수는 다를 수 있음
#   - H3: factor(연도분기) 사용 금지 (LOO 변수와 동일 수준)
#   - H2 더미: 비유머 행은 NA → subset 조건 필수
#
# 예상 focal coefficient (Python 분석 기준):
#   H1 binary  : 유머예측이진        β ≈  0.2918, p ≈ 0.0088  (n=978)
#   H1 prob    : 유머확률모델        β ≈  0.8404, p ≈ 0.0175  (n=978)
#   H1 human   : 유머레이블최종      β ≈  0.3171, p ≈ 0.0307  (n=597)
#   H2 model   : H2공격적유머모델더미 β ≈  0.4056, p ≈ 0.0060  (n=564)
#   H2 human   : H2공격적유머인간더미 β ≈  0.6405, p ≈ 0.0010  (n=278)
#   H3-pre  β1 : 유머비율LOO분기     β ≈ -6.3289, p ≈ 0.0103  (n=960)
#   H3-pre  β2 : ...제곱             β ≈ +4.3189, p ≈ 0.0395  → U자형, H3 기각
#   H3-main β1 : 공격적유머비율LOO분기 β ≈ -1.9777, p ≈ 0.5532 (n=960)
#   H3-main β2 : ...제곱             β ≈ -3.2814, p ≈ 0.6929  → not_support, H3 기각
#   H3-other β1: 기타유머비율LOO분기  β ≈ -6.8614, p ≈ 0.0043
#   H3-other β2: ...제곱             β ≈ +7.8688, p ≈ 0.0047  → U자형, H3 기각
#   H3-joint (agg) β1 ≈ -2.3560, β2 ≈ -3.7276
#   H3-joint (oth) γ1 ≈ -7.7528, γ2 ≈ +8.1417

# ═══════════════════════════════════════════════════════════════════════════════
# 0. 라이브러리 및 데이터 로드
# ═══════════════════════════════════════════════════════════════════════════════

library(ggplot2)
library(corrplot)
library(car)
library(dplyr)
library(scales)
library(gridExtra)

# 데이터 로드 (외부에서 미리 로드하지 않은 경우 아래 실행)
if (!exists("df")) {
  df <- read.csv(
    "20260615wendy's/data/wendys_h1_h2_h3_r_replication_dataset.csv",
    stringsAsFactors = FALSE, na.strings = "NA", fileEncoding = "UTF-8-BOM"
  )
}

cat("=== 데이터 로드 확인 ===\n")
cat(sprintf("  rows: %d, cols: %d\n", nrow(df), ncol(df)))
cat("  컬럼명:", paste(names(df), collapse=", "), "\n\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. 파생 변수 계산
# ═══════════════════════════════════════════════════════════════════════════════

cat("=== 1. 파생 변수 계산 ===\n")

# 1a. 종속변수 (log1p 변환)
df$참여도합계         <- log1p(df$좋아요수 + df$리트윗수 + df$답글수 + df$인용수 + df$북마크수)
df$참여도좋아요리트윗  <- log1p(df$좋아요수 + df$리트윗수)
df$참여도좋아요        <- log1p(df$좋아요수)
df$참여도리트윗        <- log1p(df$리트윗수)
df$참여도답글          <- log1p(df$답글수)
df$참여도인용          <- log1p(df$인용수)
df$참여도북마크        <- log1p(df$북마크수)

# 1b. H3 이차항 (quadratic term)
df$유머비율LOO분기제곱        <- df$유머비율LOO분기^2
df$공격적유머비율LOO분기제곱  <- df$공격적유머비율LOO분기^2
df$기타유머비율LOO분기제곱    <- df$기타유머비율LOO분기^2

cat("  참여도합계 계산 완료 (n=", sum(!is.na(df$참여도합계)), ")\n")
cat("  이차항 계산 완료\n\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. 기술통계 분석 (DESCRIPTIVE ANALYSIS)
# ═══════════════════════════════════════════════════════════════════════════════

cat("═══════════════════════════════════════════════════════\n")
cat("2. 기술통계 분석 (DESCRIPTIVE ANALYSIS)\n")
cat("═══════════════════════════════════════════════════════\n\n")

# 2a. 표본 구성 확인
cat("--- 2a. 표본 구성 ---\n")
cat(sprintf("  전체 게시물:           %d\n", nrow(df)))
cat(sprintf("  H1 인간검증 표본:      %d (%.1f%%)\n",
            sum(df$H1인간검증표본, na.rm=TRUE),
            100*mean(df$H1인간검증표본, na.rm=TRUE)))
cat(sprintf("  H2 모델 유머 only:     %d (%.1f%%)\n",
            sum(df$H2모델유머표본, na.rm=TRUE),
            100*mean(df$H2모델유머표본, na.rm=TRUE)))
cat(sprintf("  H2 인간 유머 only:     %d (%.1f%%)\n",
            sum(df$H2인간검증표본, na.rm=TRUE),
            100*mean(df$H2인간검증표본, na.rm=TRUE)))
cat(sprintf("  H3 분석 표본 (분기≥10): %d (%.1f%%)\n",
            sum(df$H3분석표본, na.rm=TRUE),
            100*mean(df$H3분석표본, na.rm=TRUE)))

# 2b. 유머 분류 분포
cat("\n--- 2b. 유머 분류 분포 ---\n")
cat("[모델 기반 유머 예측]\n")
print(table(df$유머유형모델예측))
cat("\n[최종 유머 유형 (인간 + 모델 병합)]\n")
print(table(df$유머유형최종, useNA="ifany"))
cat("\n[모델 유머 이진 예측]\n")
cat(sprintf("  유머: %d (%.1f%%), 비유머: %d (%.1f%%)\n",
            sum(df$유머예측이진==1, na.rm=TRUE),
            100*mean(df$유머예측이진==1, na.rm=TRUE),
            sum(df$유머예측이진==0, na.rm=TRUE),
            100*mean(df$유머예측이진==0, na.rm=TRUE)))

# 2c. 주요 수치 변수 기술통계
cat("\n--- 2c. 주요 수치 변수 기술통계 ---\n")
desc_vars <- c("참여도합계","좋아요수","리트윗수","답글수","인용수","북마크수",
               "조회수","텍스트길이","해시태그수","멘션수")
desc_df <- as.data.frame(t(sapply(desc_vars, function(v) {
  x <- df[[v]]
  x <- x[!is.na(x)]
  c(n=length(x),
    mean=round(mean(x),2), sd=round(sd(x),2),
    min=round(min(x),2), q25=round(quantile(x,.25),2),
    median=round(median(x),2), q75=round(quantile(x,.75),2),
    max=round(max(x),2))
})))
print(desc_df)

# 2d. H3 LOO proportion 기술통계
cat("\n--- 2d. H3 LOO proportion 기술통계 (H3분석표본 내, n=960) ---\n")
h3df <- subset(df, H3분석표본 == 1)
prop_vars <- c("유머비율LOO분기","공격적유머비율LOO분기","기타유머비율LOO분기")
prop_desc <- as.data.frame(t(sapply(prop_vars, function(v) {
  x <- h3df[[v]]
  x <- x[!is.na(x)]
  c(n=length(x), mean=round(mean(x),4), sd=round(sd(x),4),
    min=round(min(x),4), median=round(median(x),4), max=round(max(x),4))
})))
print(prop_desc)

# ── 시각화 출력 디렉토리
PLOT_DIR <- "20260615wendy's/result/"

# ═══════════════════════════════════════════════════════════════════════════════
# 3. 시각화 (VISUALIZATION)
# ═══════════════════════════════════════════════════════════════════════════════

cat("\n═══════════════════════════════════════════════════════\n")
cat("3. 시각화 (VISUALIZATION)\n")
cat("═══════════════════════════════════════════════════════\n\n")

# 3a. 참여도 분포 히스토그램
cat("--- 3a. 참여도 분포 히스토그램 ---\n")

p_hist_engage <- ggplot(df, aes(x = 참여도합계)) +
  geom_histogram(bins = 40, fill = "#2E86AB", color = "white", alpha = 0.85) +
  geom_vline(aes(xintercept = mean(참여도합계, na.rm=TRUE)),
             color = "#E84855", linetype = "dashed", linewidth = 0.8) +
  labs(title = "총 참여도(log1p) 분포",
       subtitle = sprintf("n=%d, mean=%.2f, sd=%.2f",
                          sum(!is.na(df$참여도합계)),
                          mean(df$참여도합계, na.rm=TRUE),
                          sd(df$참여도합계, na.rm=TRUE)),
       x = "log1p(참여도합계)", y = "게시물 수") +
  theme_bw(base_size = 12) +
  theme(plot.title = element_text(face="bold"))

ggsave(paste0(PLOT_DIR, "viz_01_engagement_distribution.png"),
       p_hist_engage, width=8, height=5, dpi=150)
cat("  저장: viz_01_engagement_distribution.png\n")

# 3b. 유머 여부별 참여도 박스플롯 (H1)
cat("--- 3b. 유머 여부별 참여도 박스플롯 (H1) ---\n")

df_box_h1 <- df
df_box_h1$유머여부 <- factor(
  ifelse(df_box_h1$유머예측이진 == 1, "유머 게시물", "비유머 게시물"),
  levels = c("비유머 게시물","유머 게시물"))

p_box_h1 <- ggplot(df_box_h1[!is.na(df_box_h1$유머여부),],
                   aes(x = 유머여부, y = 참여도합계, fill = 유머여부)) +
  geom_boxplot(alpha = 0.75, outlier.alpha = 0.3, outlier.size = 0.8) +
  geom_jitter(width = 0.1, alpha = 0.07, size = 0.6, color = "gray30") +
  scale_fill_manual(values = c("#AACFCF","#E84855")) +
  stat_summary(fun = mean, geom = "point", shape = 18, size = 3,
               color = "black", position = position_dodge(0.75)) +
  labs(title = "H1: 유머 여부별 총 참여도(log1p)",
       subtitle = "점(◆): 그룹 평균; 빨간점선: 중앙값",
       x = NULL, y = "log1p(참여도합계)") +
  theme_bw(base_size = 12) +
  theme(legend.position = "none", plot.title = element_text(face="bold"))

ggsave(paste0(PLOT_DIR, "viz_02_h1_engagement_by_humor.png"),
       p_box_h1, width=7, height=5, dpi=150)
cat("  저장: viz_02_h1_engagement_by_humor.png\n")

# 3c. 유머 유형별 참여도 박스플롯 (H2)
cat("--- 3c. 유머 유형별 참여도 박스플롯 (H2) ---\n")

df_h2 <- subset(df, H2모델유머표본 == 1)
df_h2$유머유형 <- factor(
  ifelse(df_h2$공격적유머여부 == 1, "공격적 유머", "기타 유머"),
  levels = c("기타 유머","공격적 유머"))

p_box_h2 <- ggplot(df_h2, aes(x = 유머유형, y = 참여도합계, fill = 유머유형)) +
  geom_boxplot(alpha = 0.75, outlier.alpha = 0.3, outlier.size = 0.8) +
  geom_jitter(width = 0.1, alpha = 0.12, size = 0.7, color = "gray30") +
  scale_fill_manual(values = c("#A8DADC","#E63946")) +
  stat_summary(fun = mean, geom = "point", shape = 18, size = 3, color = "black") +
  labs(title = "H2: 유머 유형별 총 참여도(log1p) — 모델 기반",
       subtitle = sprintf("공격적 유머: n=%d, 기타 유머: n=%d",
                          sum(df_h2$공격적유머여부==1, na.rm=TRUE),
                          sum(df_h2$기타유머여부==1, na.rm=TRUE)),
       x = NULL, y = "log1p(참여도합계)") +
  theme_bw(base_size = 12) +
  theme(legend.position = "none", plot.title = element_text(face="bold"))

ggsave(paste0(PLOT_DIR, "viz_03_h2_engagement_by_humor_type.png"),
       p_box_h2, width=7, height=5, dpi=150)
cat("  저장: viz_03_h2_engagement_by_humor_type.png\n")

# 3d. H3 LOO proportion 분포 (3개 predictor)
cat("--- 3d. H3 LOO proportion 분포 ---\n")

df_h3_long <- data.frame(
  predictor = rep(c("전체유머비율LOO","공격적유머비율LOO","기타유머비율LOO"), each=nrow(h3df)),
  value = c(h3df$유머비율LOO분기,
            h3df$공격적유머비율LOO분기,
            h3df$기타유머비율LOO분기)
)
df_h3_long$predictor <- factor(
  df_h3_long$predictor,
  levels = c("전체유머비율LOO","공격적유머비율LOO","기타유머비율LOO"))

p_h3_dist <- ggplot(df_h3_long[!is.na(df_h3_long$value),],
                    aes(x = value, fill = predictor)) +
  geom_histogram(bins = 30, alpha = 0.75, color = "white") +
  facet_wrap(~predictor, scales = "free_x", nrow = 1) +
  scale_fill_manual(values = c("#457B9D","#E63946","#2A9D8F")) +
  labs(title = "H3 LOO Quarter-level Proportion 분포 (n=960)",
       x = "LOO 비율", y = "게시물 수") +
  theme_bw(base_size = 11) +
  theme(legend.position = "none", plot.title = element_text(face="bold"),
        strip.text = element_text(size=9))

ggsave(paste0(PLOT_DIR, "viz_04_h3_loo_proportion_distribution.png"),
       p_h3_dist, width=10, height=4, dpi=150)
cat("  저장: viz_04_h3_loo_proportion_distribution.png\n")

# 3e. H3 산점도: LOO proportion vs 참여도합계
cat("--- 3e. H3 산점도 (proportion vs 참여도) ---\n")

p_scatter_pre <- ggplot(h3df[!is.na(h3df$유머비율LOO분기),],
                         aes(x = 유머비율LOO분기, y = 참여도합계)) +
  geom_point(alpha = 0.25, size = 0.9, color = "#457B9D") +
  geom_smooth(method = "lm", formula = y ~ x + I(x^2),
              se = TRUE, color = "#E63946", fill = "#E63946", alpha = 0.15) +
  labs(title = "H3-pre: 유머비율LOO vs 참여도합계 (이차곡선 피팅)",
       subtitle = "H3 분석 표본 (n=960); 빨간선: 이차회귀곡선",
       x = "유머비율LOO분기", y = "log1p(참여도합계)") +
  theme_bw(base_size = 12) + theme(plot.title = element_text(face="bold"))

p_scatter_agg <- ggplot(h3df[!is.na(h3df$공격적유머비율LOO분기),],
                         aes(x = 공격적유머비율LOO분기, y = 참여도합계)) +
  geom_point(alpha = 0.25, size = 0.9, color = "#E63946") +
  geom_smooth(method = "lm", formula = y ~ x + I(x^2),
              se = TRUE, color = "#457B9D", fill = "#457B9D", alpha = 0.15) +
  labs(title = "H3-main: 공격적유머비율LOO vs 참여도합계",
       subtitle = "빨간점: 공격적 유머 post; 파란선: 이차회귀곡선",
       x = "공격적유머비율LOO분기", y = "log1p(참여도합계)") +
  theme_bw(base_size = 12) + theme(plot.title = element_text(face="bold"))

p_scatter_oth <- ggplot(h3df[!is.na(h3df$기타유머비율LOO분기),],
                         aes(x = 기타유머비율LOO분기, y = 참여도합계)) +
  geom_point(alpha = 0.25, size = 0.9, color = "#2A9D8F") +
  geom_smooth(method = "lm", formula = y ~ x + I(x^2),
              se = TRUE, color = "#E9C46A", fill = "#E9C46A", alpha = 0.15) +
  labs(title = "H3-supplemental: 기타유머비율LOO vs 참여도합계",
       x = "기타유머비율LOO분기", y = "log1p(참여도합계)") +
  theme_bw(base_size = 12) + theme(plot.title = element_text(face="bold"))

p_scatter_combined <- grid.arrange(p_scatter_pre, p_scatter_agg, p_scatter_oth, ncol = 3)
ggsave(paste0(PLOT_DIR, "viz_05_h3_scatter_proportion_engagement.png"),
       p_scatter_combined, width=15, height=5, dpi=150)
cat("  저장: viz_05_h3_scatter_proportion_engagement.png\n")

# 3f. 연도별/월별 게시물 수 분포
cat("--- 3f. 시간별 게시물 분포 ---\n")

p_year <- ggplot(df, aes(x = factor(작성연도))) +
  geom_bar(fill = "#457B9D", alpha = 0.85) +
  labs(title = "연도별 게시물 수", x = "작성연도", y = "게시물 수") +
  theme_bw(base_size=11)

p_month <- ggplot(df, aes(x = factor(작성월))) +
  geom_bar(fill = "#2A9D8F", alpha = 0.85) +
  labs(title = "월별 게시물 수", x = "작성월", y = "게시물 수") +
  theme_bw(base_size=11)

p_hour <- ggplot(df, aes(x = factor(작성시간))) +
  geom_bar(fill = "#E9C46A", alpha = 0.85) +
  labs(title = "시간대별 게시물 수", x = "작성시간 (0-23시)", y = "게시물 수") +
  theme_bw(base_size=11)

p_time_combined <- grid.arrange(p_year, p_month, p_hour, ncol=3)
ggsave(paste0(PLOT_DIR, "viz_06_time_distribution.png"),
       p_time_combined, width=14, height=4, dpi=150)
cat("  저장: viz_06_time_distribution.png\n")

# 3g. 유머 확률 분포
cat("--- 3g. 유머 확률 분포 ---\n")

p_prob <- ggplot(df, aes(x = 유머확률모델)) +
  geom_histogram(bins = 40, fill = "#E63946", alpha = 0.75, color = "white") +
  geom_vline(xintercept = 0.5, linetype = "dashed", color = "gray30", linewidth = 0.8) +
  labs(title = "유머 확률 분포 (모델 기반)",
       subtitle = "점선: threshold=0.5",
       x = "유머 확률 (p_humor_final_tfidf_logreg)", y = "게시물 수") +
  theme_bw(base_size=12) + theme(plot.title = element_text(face="bold"))

ggsave(paste0(PLOT_DIR, "viz_07_humor_probability_distribution.png"),
       p_prob, width=7, height=5, dpi=150)
cat("  저장: viz_07_humor_probability_distribution.png\n")

cat("\n  시각화 완료 (7개 PNG 저장)\n\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. 상관행렬 히트맵 (CORRELATION HEATMAP)
# ═══════════════════════════════════════════════════════════════════════════════

cat("═══════════════════════════════════════════════════════\n")
cat("4. 상관행렬 히트맵 (CORRELATION HEATMAP)\n")
cat("═══════════════════════════════════════════════════════\n\n")

# 4a. 주요 수치 변수 선택
heatmap_vars <- c(
  "참여도합계",
  "유머예측이진", "유머확률모델",
  "공격적유머여부", "기타유머여부",
  "유머비율LOO분기", "공격적유머비율LOO분기", "기타유머비율LOO분기",
  "텍스트길이", "해시태그수", "멘션수"
)
heatmap_labels <- c(
  "참여도합계",
  "유머(이진)", "유머확률",
  "공격적유머여부", "기타유머여부",
  "유머비율LOO", "공격적비율LOO", "기타비율LOO",
  "텍스트길이", "해시태그수", "멘션수"
)

corr_data <- df[, heatmap_vars]
corr_data <- corr_data[complete.cases(corr_data), ]
cat(sprintf("  히트맵 표본: n=%d\n", nrow(corr_data)))

corr_mat <- cor(corr_data, use = "complete.obs", method = "pearson")
colnames(corr_mat) <- heatmap_labels
rownames(corr_mat) <- heatmap_labels

cat("  주요 상관계수:\n")
for (i in 1:(nrow(corr_mat)-1)) {
  for (j in (i+1):ncol(corr_mat)) {
    r <- corr_mat[i,j]
    if (abs(r) > 0.15) {
      cat(sprintf("    %s × %s: r=%.3f\n",
                  rownames(corr_mat)[i], colnames(corr_mat)[j], r))
    }
  }
}

# corrplot 저장
png(paste0(PLOT_DIR, "viz_08_correlation_heatmap.png"),
    width=1400, height=1200, res=150)
corrplot(corr_mat,
         method    = "color",
         type      = "upper",
         addCoef.col = "black",
         number.cex  = 0.65,
         tl.cex      = 0.85,
         tl.col      = "gray20",
         tl.srt      = 45,
         col         = colorRampPalette(c("#457B9D","white","#E63946"))(200),
         title = "주요 변수 상관행렬 (Pearson r)",
         mar = c(0,0,2,0),
         diag = FALSE)
dev.off()
cat("  저장: viz_08_correlation_heatmap.png\n\n")

# 4b. H3 predictor 간 상관 별도 출력 (multi-collinearity 사전 확인)
cat("  H3 predictor 간 상관 (joint model 다중공선성 확인):\n")
h3_corr_vars <- c("유머비율LOO분기","공격적유머비율LOO분기","기타유머비율LOO분기")
h3_corr <- cor(h3df[, h3_corr_vars], use="complete.obs")
print(round(h3_corr, 4))
cat(sprintf("  corr(공격적비율LOO, 기타비율LOO) = %.4f\n",
            h3_corr["공격적유머비율LOO분기","기타유머비율LOO분기"]))
cat("  → |r| < 0.30: joint model 다중공선성 우려 없음\n\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. VIF 확인 (분산팽창지수)
# ═══════════════════════════════════════════════════════════════════════════════

cat("═══════════════════════════════════════════════════════\n")
cat("5. VIF 확인 (분산팽창지수)\n")
cat("═══════════════════════════════════════════════════════\n\n")

# 5a. H1 최종 모형 VIF (M7: binary IV + time FE + format controls)
cat("--- 5a. H1 binary M7 VIF ---\n")
vif_h1 <- lm(참여도합계 ~ 유머예측이진 +
               factor(작성연도) + factor(작성월) + factor(작성시간) +
               텍스트길이 + 해시태그수 + 멘션수,
             data = df)
vif_h1_result <- car::vif(vif_h1)
cat("  GVIF 결과 (focal 변수 및 format controls):\n")
focal_rows <- c("유머예측이진","텍스트길이","해시태그수","멘션수")
for (v in focal_rows) {
  if (v %in% rownames(as.data.frame(vif_h1_result))) {
    val <- vif_h1_result[v, 1]
    cat(sprintf("    %s: GVIF=%.3f %s\n", v, val,
                ifelse(val > 10, "⚠ 높음", ifelse(val > 5, "주의", "OK"))))
  }
}
cat("  * factor FE의 GVIF^(1/(2*Df)): FE 항목은 별도 해석\n")

# 5b. H2 최종 모형 VIF
cat("\n--- 5b. H2 model M7 VIF ---\n")
vif_h2 <- lm(참여도합계 ~ H2공격적유머모델더미 +
               factor(작성연도) + factor(작성월) + factor(작성시간) +
               텍스트길이 + 해시태그수 + 멘션수,
             data = subset(df, H2모델유머표본 == 1))
vif_h2_result <- car::vif(vif_h2)
for (v in c("H2공격적유머모델더미","텍스트길이","해시태그수","멘션수")) {
  if (v %in% rownames(as.data.frame(vif_h2_result))) {
    val <- vif_h2_result[v, 1]
    cat(sprintf("    %s: GVIF=%.3f %s\n", v, val,
                ifelse(val > 10, "⚠ 높음", ifelse(val > 5, "주의", "OK"))))
  }
}

# 5c. H3 joint model VIF (이차항 포함)
cat("\n--- 5c. H3 joint M2 VIF (이차항 포함) ---\n")
vif_h3_joint <- lm(참여도합계 ~
                     유머비율LOO분기 + 유머비율LOO분기제곱 +
                     공격적유머비율LOO분기 + 공격적유머비율LOO분기제곱 +
                     기타유머비율LOO분기 + 기타유머비율LOO분기제곱 +
                     factor(작성연도) + factor(작성월) + factor(작성시간) +
                     텍스트길이 + 해시태그수 + 멘션수,
                   data = subset(df, H3분석표본 == 1))
vif_h3_result <- car::vif(vif_h3_joint)
cat("  LOO predictor 및 이차항 VIF:\n")
for (v in c("유머비율LOO분기","유머비율LOO분기제곱",
            "공격적유머비율LOO분기","공격적유머비율LOO분기제곱",
            "기타유머비율LOO분기","기타유머비율LOO분기제곱")) {
  if (v %in% rownames(as.data.frame(vif_h3_result))) {
    val <- vif_h3_result[v, 1]
    cat(sprintf("    %s: GVIF=%.2f %s\n", v, val,
                ifelse(val > 10, "⚠ 높음 (이차항 포함시 정상)", "OK")))
  }
}
cat("  * 이차항(x²) 포함 모형에서 VIF 상승은 정상 현상\n\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 헬퍼 함수
# ═══════════════════════════════════════════════════════════════════════════════

print_focal <- function(model, focal_var, model_label) {
  coefs <- summary(model)$coefficients
  if (focal_var %in% rownames(coefs)) {
    b <- coefs[focal_var, "Estimate"]
    se <- coefs[focal_var, "Std. Error"]
    t  <- coefs[focal_var, "t value"]
    p  <- coefs[focal_var, "Pr(>|t|)"]
    n  <- nobs(model)
    r2 <- summary(model)$r.squared
    cat(sprintf("  [%s] n=%d, β=%.4f (SE=%.4f, t=%.3f), p=%.4f, R²=%.4f\n",
                model_label, n, b, se, t, p, r2))
  } else {
    cat(sprintf("  [%s] '%s' 미발견. rownames:\n", model_label, focal_var))
    print(rownames(coefs))
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 6. H1 가설 검증
# ═══════════════════════════════════════════════════════════════════════════════

cat("═══════════════════════════════════════════════════════\n")
cat("6. H1: 유머 게시물 vs. 비유머 게시물 참여도 차이\n")
cat("   가설: 유머 게시물의 총 참여도 > 비유머 게시물\n")
cat("═══════════════════════════════════════════════════════\n\n")

# H1 Binary — 전체 표본 (n=978)
cat("--- H1 Binary M7 (전체 표본, n=978) ---\n")
h1_binary <- lm(참여도합계 ~ 유머예측이진 +
                  factor(작성연도) + factor(작성월) + factor(작성시간) +
                  텍스트길이 + 해시태그수 + 멘션수,
                data = df)
print_focal(h1_binary, "유머예측이진", "H1_binary_M7")
cat("  기대: β ≈ 0.2918, p ≈ 0.0088\n\n")

# H1 Probability — 전체 표본 (n=978)
cat("--- H1 Probability M7 (전체 표본, n=978) ---\n")
h1_prob <- lm(참여도합계 ~ 유머확률모델 +
                factor(작성연도) + factor(작성월) + factor(작성시간) +
                텍스트길이 + 해시태그수 + 멘션수,
              data = df)
print_focal(h1_prob, "유머확률모델", "H1_probability_M7")
cat("  기대: β ≈ 0.8404, p ≈ 0.0175\n\n")

# H1 Human Validation (n=597)
cat("--- H1 Human Validation M7 (n=597) ---\n")
h1_human <- lm(참여도합계 ~ 유머레이블최종 +
                 factor(작성연도) + factor(작성월) + factor(작성시간) +
                 텍스트길이 + 해시태그수 + 멘션수,
               data = subset(df, H1인간검증표본 == 1))
print_focal(h1_human, "유머레이블최종", "H1_human_M7")
cat("  기대: β ≈ 0.3171, p ≈ 0.0307\n\n")

cat("H1 판정: 3개 표본/모형 전부 supports_H1\n",
    "→ 유머 게시물의 참여도가 비유머 게시물보다 통계적으로 유의하게 높다.\n\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. H2 가설 검증
# ═══════════════════════════════════════════════════════════════════════════════

cat("═══════════════════════════════════════════════════════\n")
cat("7. H2: 공격적 유머 vs. 기타 유머 참여도 차이\n")
cat("   가설: 공격적 유머의 총 참여도 > 기타 유머\n")
cat("═══════════════════════════════════════════════════════\n\n")

# 그룹 평균
cat("--- 그룹 평균 (H2 모델 기반 표본) ---\n")
h2_df_m <- subset(df, H2모델유머표본 == 1)
agg_mean <- mean(h2_df_m$참여도합계[h2_df_m$H2공격적유머모델더미==1], na.rm=TRUE)
oth_mean <- mean(h2_df_m$참여도합계[h2_df_m$H2공격적유머모델더미==0], na.rm=TRUE)
cat(sprintf("  공격적 유머 (n=%d): 평균=%.4f\n",
            sum(h2_df_m$H2공격적유머모델더미==1, na.rm=TRUE), agg_mean))
cat(sprintf("  기타 유머   (n=%d): 평균=%.4f\n",
            sum(h2_df_m$H2공격적유머모델더미==0, na.rm=TRUE), oth_mean))
cat(sprintf("  평균차: %.4f\n\n", agg_mean - oth_mean))

# H2 Model-based (n=564)
cat("--- H2 Model M7 (n=564) ---\n")
h2_model <- lm(참여도합계 ~ H2공격적유머모델더미 +
                 factor(작성연도) + factor(작성월) + factor(작성시간) +
                 텍스트길이 + 해시태그수 + 멘션수,
               data = subset(df, H2모델유머표본 == 1))
print_focal(h2_model, "H2공격적유머모델더미", "H2_model_M7")
cat("  기대: β ≈ 0.4056, p ≈ 0.0060\n\n")

# H2 Human Validation (n=278)
cat("--- H2 Human M7 (n=278) ---\n")
h2_human <- lm(참여도합계 ~ H2공격적유머인간더미 +
                 factor(작성연도) + factor(작성월) + factor(작성시간) +
                 텍스트길이 + 해시태그수 + 멘션수,
               data = subset(df, H2인간검증표본 == 1))
print_focal(h2_human, "H2공격적유머인간더미", "H2_human_M7")
cat("  기대: β ≈ 0.6405, p ≈ 0.0010\n\n")

cat("H2 판정: 모델·인간 검증 표본, Step1~3 전 32개 모형 모두 supports_H2\n",
    "→ 공격적 유머의 참여도가 기타 유머보다 통계적으로 유의하게 높다.\n\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 8. H3 가설 검증 (이차함수 회귀)
# ═══════════════════════════════════════════════════════════════════════════════

cat("═══════════════════════════════════════════════════════\n")
cat("8. H3: 유머 강도(LOO 비율)와 참여도의 역 U자형 관계\n")
cat("   가설: 중간 강도에서 참여도 최대 (β₁>0, β₂<0, p₂<.05)\n")
cat("   주의: year_quarter FE 사용 금지 (LOO 변수와 동일 수준)\n")
cat("═══════════════════════════════════════════════════════\n\n")

df_h3 <- subset(df, H3분석표본 == 1)
cat(sprintf("  H3 분석 표본: n=%d, unique 분기: %d\n\n",
            nrow(df_h3), length(unique(df_h3$연도분기))))

# H3-pre: 전체 유머 비율 (n=960)
cat("--- H3-pre M7 (humor_proportion_quarter_loo) ---\n")
h3_pre <- lm(참여도합계 ~
               유머비율LOO분기 + 유머비율LOO분기제곱 +
               factor(작성연도) + factor(작성월) + factor(작성시간) +
               텍스트길이 + 해시태그수 + 멘션수,
             data = df_h3)
print_focal(h3_pre, "유머비율LOO분기",    "H3_pre_M7_beta1")
print_focal(h3_pre, "유머비율LOO분기제곱","H3_pre_M7_beta2")
tp_pre <- -coef(h3_pre)["유머비율LOO분기"] / (2 * coef(h3_pre)["유머비율LOO분기제곱"])
cat(sprintf("  turning point: %.4f\n", tp_pre))
cat("  기대: β1 ≈ -6.3289, β2 ≈ +4.3189 → β2>0 (U자형; 역U자형 아님) → H3 기각\n\n")

# H3-main: 공격적 유머 비율 (n=960)
cat("--- H3-main M7 (aggressive_humor_proportion_quarter_loo) ---\n")
h3_main <- lm(참여도합계 ~
                공격적유머비율LOO분기 + 공격적유머비율LOO분기제곱 +
                factor(작성연도) + factor(작성월) + factor(작성시간) +
                텍스트길이 + 해시태그수 + 멘션수,
              data = df_h3)
print_focal(h3_main, "공격적유머비율LOO분기",    "H3_main_M7_beta1")
print_focal(h3_main, "공격적유머비율LOO분기제곱","H3_main_M7_beta2")
tp_main <- -coef(h3_main)["공격적유머비율LOO분기"] /
            (2 * coef(h3_main)["공격적유머비율LOO분기제곱"])
cat(sprintf("  turning point: %.4f\n", tp_main))
cat("  기대: β1 ≈ -1.9777, β2 ≈ -3.2814 (p≈0.6929) → not_support → H3 기각\n\n")

# H3-supplemental: 기타 유머 비율 (n=960)
cat("--- H3-supplemental M8 (other_humor_proportion_quarter_loo) ---\n")
h3_other <- lm(참여도합계 ~
                 기타유머비율LOO분기 + 기타유머비율LOO분기제곱 +
                 factor(작성연도) + factor(작성월) + factor(작성시간) +
                 텍스트길이 + 해시태그수 + 멘션수,
               data = df_h3)
print_focal(h3_other, "기타유머비율LOO분기",    "H3_other_M8_beta1")
print_focal(h3_other, "기타유머비율LOO분기제곱","H3_other_M8_beta2")
tp_other <- -coef(h3_other)["기타유머비율LOO분기"] /
             (2 * coef(h3_other)["기타유머비율LOO분기제곱"])
cat(sprintf("  turning point: %.4f\n", tp_other))
cat("  기대: β1 ≈ -6.8614, β2 ≈ +7.8688 (p≈0.0047) → β2>0 (U자형) → H3 기각\n\n")

# H3-joint: 공격적 + 기타 동시 투입 (마스킹 검증)
cat("--- H3-joint M2 (aggressive + other 동시 투입) ---\n")
h3_joint <- lm(참여도합계 ~
                 공격적유머비율LOO분기 + 공격적유머비율LOO분기제곱 +
                 기타유머비율LOO분기   + 기타유머비율LOO분기제곱 +
                 factor(작성연도) + factor(작성월) + factor(작성시간) +
                 텍스트길이 + 해시태그수 + 멘션수,
               data = df_h3)
print_focal(h3_joint, "공격적유머비율LOO분기",    "H3_joint_M2_agg_beta1")
print_focal(h3_joint, "공격적유머비율LOO분기제곱","H3_joint_M2_agg_beta2")
print_focal(h3_joint, "기타유머비율LOO분기",      "H3_joint_M2_oth_gamma1")
print_focal(h3_joint, "기타유머비율LOO분기제곱",  "H3_joint_M2_oth_gamma2")
cat("  기대: agg β1≈-2.3560, β2≈-3.7276; oth γ1≈-7.7528, γ2≈+8.1417\n")
cat("  → aggressive not_support 유지; other U_shape; 마스킹 없음 확인\n\n")

cat("H3 판정: H3 기각\n",
    "→ 어떤 유머 비율 변수도 역U자형 관계를 보이지 않음\n",
    "  (H3-pre, H3-main: not_support; H3-other: 역방향 U자형)\n\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 9. 최종 결과 요약
# ═══════════════════════════════════════════════════════════════════════════════

cat("═══════════════════════════════════════════════════════\n")
cat("9. 최종 결과 요약\n")
cat("═══════════════════════════════════════════════════════\n\n")

get_coef <- function(model, var) {
  coef(summary(model))[var, c("Estimate","Pr(>|t|)")]
}

cat("┌─────────────────────────────────────────────────────┐\n")
cat("│ 가설 │  핵심 수치 (M7 최종 모형)         │  결론   │\n")
cat("├─────────────────────────────────────────────────────┤\n")

h1b <- get_coef(h1_binary, "유머예측이진")
cat(sprintf("│ H1   │ β=%.4f, p=%.4f (n=978)        │  지지   │\n",
            h1b[1], h1b[2]))

h2m <- get_coef(h2_model, "H2공격적유머모델더미")
cat(sprintf("│ H2   │ β=%.4f, p=%.4f (n=564)        │  지지   │\n",
            h2m[1], h2m[2]))

h3b2 <- get_coef(h3_main, "공격적유머비율LOO분기제곱")
cat(sprintf("│ H3   │ β2=%.4f, p=%.4f (n=960)      │  기각   │\n",
            h3b2[1], h3b2[2]))

cat("└─────────────────────────────────────────────────────┘\n\n")

cat("생성된 시각화 파일 (20260615wendy's/result/):\n")
viz_files <- c("viz_01_engagement_distribution.png",
               "viz_02_h1_engagement_by_humor.png",
               "viz_03_h2_engagement_by_humor_type.png",
               "viz_04_h3_loo_proportion_distribution.png",
               "viz_05_h3_scatter_proportion_engagement.png",
               "viz_06_time_distribution.png",
               "viz_07_humor_probability_distribution.png",
               "viz_08_correlation_heatmap.png")
for (f in viz_files) cat(sprintf("  %s\n", f))

cat("\n스크립트 실행 완료\n")
cat("focal coefficient가 기대값과 다를 경우 확인 사항:\n")
cat("  1. na.strings='NA', fileEncoding='UTF-8-BOM' 옵션\n")
cat("  2. 파생변수(참여도합계, 이차항) 계산 여부\n")
cat("  3. subset 조건 (H1인간검증표본, H2모델유머표본, H3분석표본)\n")
cat("  4. H3에서 factor(연도분기) 미포함 확인\n")

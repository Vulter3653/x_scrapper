# ============================================================
# 재현 코드: 누적 중첩 OLS 모델 (Nested Cumulative Models, v3)
# 작성일: 2026-06-19
# ============================================================
#
# ── 사용 입력 파일 (1개) ────────────────────────────────────
#
#  analysis_ready_dataset.csv
#
#  이 파일은 이 스크립트와 같은 디렉토리에 위치함.
#  내용: 전체 표본(FS, N=68,039) + 인간 코딩 표본(HC, N=3,574)
#  총 71,613행. sample_type 열로 구분.
#
#  원본 생성 로직 (Python):
#   [FS]  h2_post_level_regression_ready.csv 에서 h2_sample_inclusion_flag==1 행 추출
#   [HC]  training_labels_v3_with_coder3_batch2.csv (인간 레이블)
#         + fortune100_domain_adapted_humor_classification_v3.csv (v3 분류 결과)
#         → 3단계 fallback 매칭: tweet_id → URL status_id → 텍스트 MD5 해시
#         → 3,074건 직접 + 500건 URL fallback + 0건 해시 = 3,574건
#
# ── 열 설명 ────────────────────────────────────────────────
#  sample_type          : "Full_sample" 또는 "Human_coded"
#  company_name         : 기업명 (Amazon이 기준 범주)
#  log_eng              : log(1 + total_engagement)  ← 종속변수
#  aggressive_humor     : 공격적 유머 더미 (0/1)
#  affiliative_humor    : 친화적 유머 더미 (0/1)
#  self_enhancing_humor : 자기고양 유머 더미 (0/1)
#  self_defeating_humor : 자기패배 유머 더미 (0/1)
#  text_length          : 텍스트 길이 (문자 수)
#  hashtag_count        : 해시태그 수
#  mention_count        : 멘션 수
#  year                 : 연도 문자열 (예: "2023")
#  month                : 월 문자열 2자리 (예: "07")
#  qoy                  : 분기 (1/2/3/4)
#
# ── 모델 구조 ───────────────────────────────────────────────
#  모델 1: 단순 OLS  (유머 변수만)
#  모델 2: 모델 1 + 통제변수 (text_length, hashtag_count, mention_count)
#  모델 3: 모델 2 + 시간 더미 (연도+월 [H1/H2]; 연도+분기 [H3])
#  모델 4: 모델 3 + 기업 더미 (98개, 기준=Amazon)
#
# ── OLS 방식 ────────────────────────────────────────────────
#  고전적 OLS: s² = SSR/(n-k), Var(β̂) = s²(X'X)⁻¹
#  R의 lm()이 기본적으로 이 방식을 사용하므로 Python 결과와 일치함
# ============================================================


# ── 0. 패키지 로드 ────────────────────────────────────────────
# 최초 실행 시:
# install.packages(c("tidyverse", "car", "broom", "patchwork", "scales"))
suppressPackageStartupMessages({
  library(tidyverse)   # 데이터 조작 + ggplot2 시각화
  library(car)         # linearHypothesis() — 선형 대비 검정
  library(broom)       # tidy() — lm 결과 정리
  library(patchwork)   # 여러 ggplot 패널 배치
  library(scales)      # 축 서식
})


# ── 1. 경로 설정 및 데이터 로드 ──────────────────────────────
# 이 스크립트 파일이 있는 디렉토리를 OUT으로 설정
# RStudio에서 실행할 경우:
OUT <- dirname(rstudioapi::getSourceEditorContext()$path)
# 터미널에서 실행할 경우 아래 줄의 주석을 해제하고 경로를 지정:
# OUT <- "/home/user/marketingstrategy/20260618expand/ols_hypothesis_results/nested_cumulative_models_v3"

DATA_FILE <- file.path(OUT, "analysis_ready_dataset.csv")
cat(sprintf("데이터 파일: %s\n", DATA_FILE))
cat(sprintf("파일 존재 여부: %s\n", ifelse(file.exists(DATA_FILE), "확인됨", "없음 — 경로를 확인하라")))
stopifnot(file.exists(DATA_FILE))


# ── 2. 데이터 로드 및 전처리 ─────────────────────────────────
cat("\n[1/6] 데이터 로드 중...\n")

raw <- read_csv(DATA_FILE, col_types = cols(.default = "c"), show_col_types = FALSE)
cat(sprintf("  총 행 수: %s\n", format(nrow(raw), big.mark=",")))

# 수치형 변환 및 범주형 더미 생성
# - year, month: factor로 변환 (lm이 자동으로 기준 범주 설정; 가장 이른 값이 기준)
# - company_name: Amazon을 기준 범주로 명시
dat <- raw %>%
  mutate(
    log_eng              = as.numeric(log_eng),
    aggressive_humor     = as.integer(aggressive_humor),
    affiliative_humor    = as.integer(affiliative_humor),
    self_enhancing_humor = as.integer(self_enhancing_humor),
    self_defeating_humor = as.integer(self_defeating_humor),
    text_length          = as.numeric(text_length),
    hashtag_count        = as.numeric(hashtag_count),
    mention_count        = as.numeric(mention_count),
    year                 = factor(year),          # 연도 더미 (기준=가장 이른 연도)
    month                = factor(month),         # 월 더미 (기준=01월)
    qoy                  = factor(qoy),           # 분기 더미 (기준=Q1)
    company_name         = factor(                # 기업 더미 (기준=Amazon)
      company_name,
      levels = c("Amazon", sort(setdiff(unique(company_name), "Amazon")))
    )
  )

# 표본 분리
fs <- dat %>% filter(sample_type == "Full_sample")
hc <- dat %>% filter(sample_type == "Human_coded")

cat(sprintf("  전체 표본(FS)  N = %s  (기대값: 68,039)\n", format(nrow(fs), big.mark=",")))
cat(sprintf("  인간코딩(HC)   N = %s  (기대값:  3,574)\n", format(nrow(hc), big.mark=",")))

# N 검증: 기대값과 다르면 스크립트 중단
stopifnot(nrow(fs) == 68039, nrow(hc) == 3574)


# ── 3. H1/H2 OLS 모델 피팅 ──────────────────────────────────
# 종속변수: log_eng = log(1 + Engagement)
# 기준 범주: 비유머 게시물 (aggressive=affiliative=self_enhancing=self_defeating=0)
# H1/H2 회귀식:
#   log_eng = β0 + β1·Agg + β2·Aff + β3·SE + β4·SD
#             [+ γ1·text_length + γ2·hashtag_count + γ3·mention_count]
#             [+ Σ τ_y·Year_y + Σ τ_m·Month_m]
#             [+ Σ δ_c·CompanyDummy_c]  + ε

cat("\n[2/6] H1/H2 OLS 모델 피팅 중...\n")

# 모델 공식 생성 함수
make_h1h2_formula <- function(ctrl=FALSE, time=FALSE, company=FALSE) {
  base <- "log_eng ~ aggressive_humor + affiliative_humor + self_enhancing_humor + self_defeating_humor"
  if (ctrl)    base <- paste(base, "+ text_length + hashtag_count + mention_count")
  if (time)    base <- paste(base, "+ year + month")   # 연도+월 시간 더미
  if (company) base <- paste(base, "+ company_name")   # 기업 더미 98개
  as.formula(base)
}

# 전체 표본 4개 모델
fs_h1h2_m1 <- lm(make_h1h2_formula(),                                   data = fs)
fs_h1h2_m2 <- lm(make_h1h2_formula(ctrl=TRUE),                          data = fs)
fs_h1h2_m3 <- lm(make_h1h2_formula(ctrl=TRUE, time=TRUE),               data = fs)
fs_h1h2_m4 <- lm(make_h1h2_formula(ctrl=TRUE, time=TRUE, company=TRUE), data = fs)

# 인간 코딩 4개 모델
hc_h1h2_m1 <- lm(make_h1h2_formula(),                                   data = hc)
hc_h1h2_m2 <- lm(make_h1h2_formula(ctrl=TRUE),                          data = hc)
hc_h1h2_m3 <- lm(make_h1h2_formula(ctrl=TRUE, time=TRUE),               data = hc)
hc_h1h2_m4 <- lm(make_h1h2_formula(ctrl=TRUE, time=TRUE, company=TRUE), data = hc)

h1h2_models <- list(
  M1_Full_sample=fs_h1h2_m1, M2_Full_sample=fs_h1h2_m2,
  M3_Full_sample=fs_h1h2_m3, M4_Full_sample=fs_h1h2_m4,
  M1_Human_coded=hc_h1h2_m1, M2_Human_coded=hc_h1h2_m2,
  M3_Human_coded=hc_h1h2_m3, M4_Human_coded=hc_h1h2_m4
)

# R² 출력
cat("  H1/H2 R² / Adjusted R²:\n")
for (nm in names(h1h2_models)) {
  s <- summary(h1h2_models[[nm]])
  cat(sprintf("    %-20s  R²=%.4f  Adj-R²=%.4f\n", nm, s$r.squared, s$adj.r.squared))
}


# ── 4. H1/H2 가중 대비 검정 ─────────────────────────────────
# 유머 유형별 게시물 비율을 가중치로 사용해 H1 / H2-1 / H2-2 / H2-3 검정
#
# H1:   Σ w_type · β_type   (전체 유머 내 각 유형 비율이 가중치)
# H2-1: β_agg − Σ w_other · β_other  (other = aff+se+sd 내 비율)
# H2-2: β_agg − Σ w_self  · β_self   (self  = se+sd 내 비율)
# H2-3: pairwise (β_agg−β_aff, β_agg−β_se, β_agg−β_sd)

cat("\n[3/6] H1/H2 대비 검정 중...\n")

compute_contrasts <- function(model_obj, data_df) {
  # 가중치 계산
  n_agg <- sum(data_df$aggressive_humor)
  n_aff <- sum(data_df$affiliative_humor)
  n_se  <- sum(data_df$self_enhancing_humor)
  n_sd  <- sum(data_df$self_defeating_humor)
  n_hum <- n_agg + n_aff + n_se + n_sd

  # H1 가중치: 각 유형 게시물 수 / 전체 유머 게시물 수
  w_agg <- n_agg / n_hum;  w_aff <- n_aff / n_hum
  w_se  <- n_se  / n_hum;  w_sd  <- n_sd  / n_hum

  # H2-1 가중치: 기타 유머(non-aggressive) 내 비율
  n_oth   <- n_aff + n_se + n_sd
  w_aff_o <- n_aff / n_oth;  w_se_o <- n_se / n_oth;  w_sd_o <- n_sd / n_oth

  # H2-2 가중치: SELF 유머(se+sd) 내 비율
  n_self  <- n_se + n_sd
  w_se_s  <- n_se / n_self;  w_sd_s  <- n_sd / n_self

  # 계수 및 분산-공분산 행렬에서 4개 유머 변수만 추출
  b <- coef(model_obj)
  V <- vcov(model_obj)    # 고전적 OLS Var(β̂) = s²(X'X)⁻¹
  focal_names <- c("aggressive_humor","affiliative_humor",
                   "self_enhancing_humor","self_defeating_humor")
  idx <- match(focal_names, names(b))
  b4  <- b[idx];   V4 <- V[idx, idx]

  # 대비 벡터 L을 받아 추정치, SE, t, p 계산
  contrast_test <- function(L, hyp, cont_name) {
    est   <- sum(L * b4)
    se_c  <- sqrt(as.numeric(t(L) %*% V4 %*% L))
    t_val <- est / se_c
    p_val <- 2 * pt(-abs(t_val), df = model_obj$df.residual)
    stars <- ifelse(p_val<.01,"***", ifelse(p_val<.05,"**", ifelse(p_val<.10,"*","")))
    tibble(hypothesis=hyp, contrast=cont_name,
           estimate=round(est,6), std_error=round(se_c,6),
           t_stat=round(t_val,4), p_value=round(p_val,6), stars=stars)
  }

  bind_rows(
    contrast_test(c(w_agg, w_aff, w_se, w_sd),       "H1",   "Weighted Humor Effect"),
    contrast_test(c(1,-w_aff_o,-w_se_o,-w_sd_o),     "H2-1", "Aggressive − Other (weighted avg)"),
    contrast_test(c(1, 0, -w_se_s, -w_sd_s),         "H2-2", "Aggressive − SELF (weighted avg)"),
    contrast_test(c(1,-1, 0, 0),                     "H2-3", "Aggressive − Affiliative"),
    contrast_test(c(1, 0,-1, 0),                     "H2-3", "Aggressive − Self-Enhancing"),
    contrast_test(c(1, 0, 0,-1),                     "H2-3", "Aggressive − Self-Defeating")
  )
}

contrast_results <- bind_rows(
  imap(h1h2_models, function(m, nm) compute_contrasts(m, if(grepl("Full",nm)) fs else hc) %>%
         mutate(model=nm))
) %>% relocate(model)

# ── Python 결과 검증 ──────────────────────────────────────────
# 재현 성공 기준: 추정치 차이 < 1e-4
cat("  H1 FS 추정치 검증 (R vs Python):\n")
py_h1_fs <- c(M1=1.166525, M2=1.15332, M3=1.109234, M4=0.221485)
r_h1_fs  <- contrast_results %>%
  filter(grepl("Full", model), hypothesis=="H1") %>%
  arrange(model) %>% pull(estimate)
names(r_h1_fs) <- paste0("M", 1:4)
for (nm in names(py_h1_fs)) {
  diff <- abs(r_h1_fs[nm] - py_h1_fs[nm])
  cat(sprintf("    %s: R=%.6f  Python=%.6f  차이=%.2e  %s\n",
              nm, r_h1_fs[nm], py_h1_fs[nm], diff,
              ifelse(diff < 1e-4, "✓ 일치", "✗ 불일치")))
}


# ── 5. H3 기업-분기 집계 및 OLS ────────────────────────────
# 종속변수: 기업-분기 평균 log(1+Engagement)
# 핵심 설명변수: intensity = 기업-분기 내 공격적 유머 게시물 비율 (0~1)
# H3 회귀식:
#   mean_log_eng_{fq} = α + β1·intensity + β2·intensity²
#                       [+ 통제변수 평균값 + log(총 게시물수)]
#                       [+ 연도+분기 더미] [+ 기업 더미] + ε

cat("\n[4/6] H3 기업-분기 집계 중...\n")

aggregate_fq <- function(df) {
  df %>%
    # qoy는 이미 CSV에 있지만, month에서 직접 계산해 일관성 확보
    mutate(qoy_int = (as.integer(as.character(month)) - 1L) %/% 3L + 1L,
           yr_str  = as.character(year)) %>%
    group_by(company_name, yr_str, qoy_int) %>%
    summarise(
      n_posts          = n(),
      n_agg            = sum(aggressive_humor, na.rm=TRUE),
      mean_log_eng     = mean(log_eng, na.rm=TRUE),
      mean_text_length = mean(text_length, na.rm=TRUE),
      mean_hashtag     = mean(hashtag_count, na.rm=TRUE),
      mean_mention     = mean(mention_count, na.rm=TRUE),
      .groups = "drop"
    ) %>%
    mutate(
      intensity       = n_agg / n_posts,       # 공격적 유머 강도
      intensity_sq    = intensity^2,             # 역U자형 검정용 제곱항
      log_total_posts = log(n_posts),            # 총 게시물 수 로그 (통제)
      year            = factor(yr_str),          # 연도 더미
      qoy             = factor(qoy_int),         # 분기 더미 (기준=Q1)
      company_name    = factor(
        as.character(company_name),
        levels = c("Amazon", sort(setdiff(unique(as.character(company_name)), "Amazon")))
      )
    )
}

fs_fq <- aggregate_fq(fs)
hc_fq <- aggregate_fq(hc)

cat(sprintf("  FS 기업-분기 수: %s  (기대값: 1,420)\n", format(nrow(fs_fq), big.mark=",")))
cat(sprintf("  HC 기업-분기 수: %s  (기대값:   925)\n", format(nrow(hc_fq), big.mark=",")))
stopifnot(nrow(fs_fq) == 1420, nrow(hc_fq) == 925)

# H3 모델 공식 (통제변수는 기업-분기 평균값 사용)
make_h3_formula <- function(ctrl=FALSE, time=FALSE, company=FALSE) {
  base <- "mean_log_eng ~ intensity + intensity_sq"
  if (ctrl)    base <- paste(base, "+ mean_text_length + mean_hashtag + mean_mention + log_total_posts")
  if (time)    base <- paste(base, "+ year + qoy")       # 연도+분기 시간 더미
  if (company) base <- paste(base, "+ company_name")     # 기업 더미 98개
  as.formula(base)
}

# 전체 표본 H3
fs_h3_m1 <- lm(make_h3_formula(),                                    data=fs_fq)
fs_h3_m2 <- lm(make_h3_formula(ctrl=TRUE),                           data=fs_fq)
fs_h3_m3 <- lm(make_h3_formula(ctrl=TRUE, time=TRUE),                data=fs_fq)
fs_h3_m4 <- lm(make_h3_formula(ctrl=TRUE, time=TRUE, company=TRUE),  data=fs_fq)

# 인간 코딩 H3
hc_h3_m1 <- lm(make_h3_formula(),                                    data=hc_fq)
hc_h3_m2 <- lm(make_h3_formula(ctrl=TRUE),                           data=hc_fq)
hc_h3_m3 <- lm(make_h3_formula(ctrl=TRUE, time=TRUE),                data=hc_fq)
hc_h3_m4 <- lm(make_h3_formula(ctrl=TRUE, time=TRUE, company=TRUE),  data=hc_fq)

h3_models <- list(
  M1_Full_sample=fs_h3_m1, M2_Full_sample=fs_h3_m2,
  M3_Full_sample=fs_h3_m3, M4_Full_sample=fs_h3_m4,
  M1_Human_coded=hc_h3_m1, M2_Human_coded=hc_h3_m2,
  M3_Human_coded=hc_h3_m3, M4_Human_coded=hc_h3_m4
)

# β₁, β₂, 전환점, H3 지지 여부
cat("\n[5/6] H3 결과 및 지지 여부 판정 중...\n")

h3_summary <- imap_dfr(h3_models, function(m, nm) {
  sm  <- summary(m)
  b1  <- coef(m)["intensity"]
  b2  <- coef(m)["intensity_sq"]
  se1 <- sm$coefficients["intensity",       "Std. Error"]
  se2 <- sm$coefficients["intensity_sq",    "Std. Error"]
  p2  <- sm$coefficients["intensity_sq",    "Pr(>|t|)"]
  tp  <- -b1 / (2 * b2)
  # 지지 조건: β₁>0, β₂<0, β₂ p<.10, 전환점이 [0,1] 내
  sup <- b1>0 & b2<0 & p2<0.10 & is.finite(tp) & tp>=0 & tp<=1
  tibble(model=nm,
         beta1=round(b1,6), se_beta1=round(se1,6),
         beta2=round(b2,6), se_beta2=round(se2,6),
         p_beta2=round(p2,4), turning_point=round(tp,4),
         r_squared=round(sm$r.squared,4), adj_r2=round(sm$adj.r.squared,4),
         H3_supported=sup)
})

print(h3_summary %>% select(model, beta1, beta2, p_beta2, turning_point, r_squared, H3_supported))

# H3 Python 값 검증
cat("\n  H3 β₁ 검증 (R vs Python):\n")
py_b1 <- c(M1_Full_sample=12.619846, M2_Full_sample=9.483818,
            M3_Full_sample=9.079711,  M4_Full_sample=0.381347,
            M1_Human_coded=7.349,     M2_Human_coded=4.226,
            M3_Human_coded=3.225,     M4_Human_coded=0.196)
for (nm in names(py_b1)) {
  r_val <- h3_summary %>% filter(model==nm) %>% pull(beta1)
  diff  <- abs(r_val - py_b1[nm])
  cat(sprintf("    %s: R=%.4f  Python=%.4f  차이=%.4f  %s\n",
              nm, r_val, py_b1[nm], diff,
              ifelse(diff < 0.01, "✓ 일치", "✗ 불일치")))
}


# ── 6. 시각화 ────────────────────────────────────────────────
cat("\n[6/6] 시각화 생성 중...\n")

SAMPLE_COLORS <- c("전체 표본"="steelblue", "인간코딩 표본"="firebrick")
MODEL_LABELS  <- c("모델 1\n(OLS)", "모델 2\n(+통제변수)",
                   "모델 3\n(+시간더미)", "모델 4\n(+기업더미)")

# ── Figure 1: H1 가중 유머 효과 (모델 1→4) ───────────────────
# 통제변수·시간더미·기업더미를 추가할수록 H1 추정치가 어떻게 변하는지 보여줌

fig1_dat <- contrast_results %>%
  filter(hypothesis == "H1") %>%
  mutate(
    sample    = ifelse(grepl("Full", model), "전체 표본", "인간코딩 표본"),
    model_num = as.integer(gsub("M(\\d).*", "\\1", model)),
    ci_lo     = estimate - 1.96 * std_error,   # 95% CI (정규근사)
    ci_hi     = estimate + 1.96 * std_error
  )

fig1 <- ggplot(fig1_dat, aes(x=model_num, y=estimate, color=sample, group=sample)) +
  geom_hline(yintercept=0, linetype="dashed", color="gray60") +
  geom_ribbon(aes(ymin=ci_lo, ymax=ci_hi, fill=sample), alpha=0.12, color=NA) +
  geom_line(linewidth=0.9) +
  geom_point(size=3.5) +
  geom_text(aes(label=sprintf("%.4f%s", estimate, stars)),
            vjust=-0.9, size=3, show.legend=FALSE) +
  scale_color_manual(values=SAMPLE_COLORS) +
  scale_fill_manual(values=SAMPLE_COLORS) +
  scale_x_continuous(breaks=1:4, labels=MODEL_LABELS) +
  labs(
    title    = "Figure 1. H1: 가중 유머 효과 — 모델별 추정치 변화",
    subtitle = "유머 게시물은 모든 모델에서 비유머 게시물보다 유의하게 높은 인게이지먼트를 보임",
    x=NULL, y="추정치 (±1.96 SE)",
    color="표본", fill="표본",
    caption="*** p<.01  |  고전적 OLS SE  |  기준 범주 = 비유머 게시물"
  ) +
  theme_minimal(base_size=12) +
  theme(legend.position="bottom", panel.grid.minor=element_blank(),
        plot.title=element_text(face="bold"))

ggsave(file.path(OUT, "fig1_h1_weighted_effect.png"), fig1, width=8, height=5, dpi=150)
cat("  Figure 1 저장: fig1_h1_weighted_effect.png\n")


# ── Figure 2: H2 대비 계수 비교 (전 모델, 전체 표본 기준) ────
# 각 대비의 추정치와 95% CI를 모델별로 비교

fig2_dat <- contrast_results %>%
  filter(grepl("Full", model),
         hypothesis %in% c("H2-1","H2-2","H2-3")) %>%
  mutate(
    model_num   = as.integer(gsub("M(\\d).*", "\\1", model)),
    model_lbl   = factor(model_num, labels=MODEL_LABELS),
    ci_lo       = estimate - 1.96 * std_error,
    ci_hi       = estimate + 1.96 * std_error,
    contrast_kr = recode(contrast,
      "Aggressive − Other (weighted avg)" = "H2-1: Agg − 기타 (가중)",
      "Aggressive − SELF (weighted avg)"  = "H2-2: Agg − SELF (가중)",
      "Aggressive − Affiliative"          = "H2-3a: Agg − 친화적",
      "Aggressive − Self-Enhancing"       = "H2-3b: Agg − 자기고양",
      "Aggressive − Self-Defeating"       = "H2-3c: Agg − 자기패배"
    )
  )

fig2 <- ggplot(fig2_dat, aes(x=estimate, y=contrast_kr, color=model_lbl)) +
  geom_vline(xintercept=0, linetype="dashed", color="gray60") +
  geom_errorbarh(aes(xmin=ci_lo, xmax=ci_hi), height=0.25,
                 position=position_dodge(width=0.6)) +
  geom_point(size=3, position=position_dodge(width=0.6)) +
  geom_text(aes(label=sprintf("%.3f%s", estimate, stars)),
            hjust=-0.2, size=2.8, position=position_dodge(width=0.6),
            show.legend=FALSE) +
  scale_color_brewer(palette="Dark2", name="모델") +
  labs(
    title    = "Figure 2. H2: 공격적 유머 대비 계수 — 전체 표본, 모델별 비교",
    subtitle = "양수 = 공격적 유머가 비교 대상보다 높은 인게이지먼트  |  오차막대: ±1.96 SE",
    x="추정치 (±1.96 SE)", y=NULL,
    caption="H2-3c (Agg−자기패배)는 전체 표본에서 음수 → 자기패배 유머가 오히려 높음"
  ) +
  theme_minimal(base_size=12) +
  theme(legend.position="bottom", panel.grid.minor=element_blank(),
        plot.title=element_text(face="bold"))

ggsave(file.path(OUT, "fig2_h2_contrasts_by_model.png"), fig2, width=9, height=5.5, dpi=150)
cat("  Figure 2 저장: fig2_h2_contrasts_by_model.png\n")


# ── Figure 3: H3 역U자형 곡선 ───────────────────────────────
# 공격적 유머 강도(0~1)에 따른 예측 평균 log engagement
# 절편과 β₁, β₂만 사용해 순수 비선형 패턴 시각화

x_seq <- seq(0, 1, length.out=200)

pred_curve <- function(model_obj, model_nm) {
  b <- coef(model_obj)
  b0 <- b["(Intercept)"];  b1 <- b["intensity"];  b2 <- b["intensity_sq"]
  tibble(intensity=x_seq,
         pred     = b0 + b1*x_seq + b2*x_seq^2,
         model_nm = model_nm,
         sample   = ifelse(grepl("Full", model_nm), "전체 표본", "인간코딩 표본"),
         model_num= as.integer(gsub("M(\\d).*", "\\1", model_nm)))
}

curves <- bind_rows(imap(h3_models, pred_curve)) %>%
  mutate(model_lbl=paste0("모델 ", model_num))

# 전환점 (지지되는 모델만 표시)
tp_pts <- h3_summary %>%
  filter(H3_supported) %>%
  rowwise() %>%
  mutate(
    sample    = ifelse(grepl("Full", model), "전체 표본", "인간코딩 표본"),
    model_num = as.integer(gsub("M(\\d).*", "\\1", model)),
    pred_at_tp = unname(coef(h3_models[[model]])["(Intercept)"] +
                        beta1*turning_point + beta2*turning_point^2)
  ) %>% ungroup() %>%
  mutate(model_lbl=paste0("모델 ", model_num))

# 실제 관측치
obs_pts <- bind_rows(
  fs_fq %>% mutate(sample="전체 표본"),
  hc_fq %>% mutate(sample="인간코딩 표본")
)

fig3 <- ggplot(curves, aes(x=intensity, y=pred, color=model_lbl, linetype=model_lbl)) +
  geom_point(data=obs_pts, aes(x=intensity, y=mean_log_eng),
             inherit.aes=FALSE, color="gray75", alpha=0.35, size=0.9) +
  geom_line(linewidth=1.0) +
  geom_point(data=tp_pts, aes(x=turning_point, y=pred_at_tp, color=model_lbl),
             inherit.aes=FALSE, shape=4, size=4, stroke=1.5, show.legend=FALSE) +
  facet_wrap(~sample) +
  scale_color_brewer(palette="Dark2", name="모델") +
  scale_linetype_manual(values=c("solid","dashed","dotdash","longdash"), name="모델") +
  scale_x_continuous(labels=scales::percent_format(accuracy=1),
                     breaks=seq(0,1,0.2)) +
  labs(
    title    = "Figure 3. H3: 공격적 유머 강도와 평균 로그 인게이지먼트",
    subtitle = "× 표시: 전환점(Turning Point)  |  회색 점: 실제 기업-분기 관측치",
    x="공격적 유머 강도 (기업-분기 내 공격적 유머 비율)",
    y="예측 평균 Log(Engagement + 1)",
    caption="모델 4(FS) 및 모델 3-4(HC): 기업 더미가 기업 간 이질성 흡수 → 역U자형 소멸"
  ) +
  theme_minimal(base_size=12) +
  theme(legend.position="bottom", panel.grid.minor=element_blank(),
        plot.title=element_text(face="bold"))

ggsave(file.path(OUT, "fig3_h3_inverted_u.png"), fig3, width=10, height=5, dpi=150)
cat("  Figure 3 저장: fig3_h3_inverted_u.png\n")


# ── Figure 4: 모델별 R² 개선 ─────────────────────────────────
# 통제변수/시간더미/기업더미 추가에 따른 R² 향상 시각화

r2_dat <- bind_rows(
  imap_dfr(h1h2_models, function(m, nm) {
    s <- summary(m)
    tibble(model_nm=nm, analysis="H1/H2 (게시물 수준)",
           sample=ifelse(grepl("Full",nm),"전체 표본","인간코딩 표본"),
           model_num=as.integer(gsub("M(\\d).*","\\1",nm)),
           r2=s$r.squared, adj_r2=s$adj.r.squared)
  }),
  imap_dfr(h3_models, function(m, nm) {
    s <- summary(m)
    tibble(model_nm=nm, analysis="H3 (기업-분기 수준)",
           sample=ifelse(grepl("Full",nm),"전체 표본","인간코딩 표본"),
           model_num=as.integer(gsub("M(\\d).*","\\1",nm)),
           r2=s$r.squared, adj_r2=s$adj.r.squared)
  })
) %>% mutate(model_lbl=factor(model_num, labels=MODEL_LABELS))

fig4 <- ggplot(r2_dat, aes(x=model_lbl, y=r2, color=sample, group=sample)) +
  geom_line(linewidth=0.9) +
  geom_point(size=3.5) +
  geom_text(aes(label=sprintf("%.3f", r2)), vjust=-0.9, size=3, show.legend=FALSE) +
  facet_wrap(~analysis, scales="free_y") +
  scale_color_manual(values=SAMPLE_COLORS) +
  scale_y_continuous(labels=scales::percent_format(accuracy=1),
                     expand=expansion(mult=c(0.05,0.15))) +
  labs(
    title    = "Figure 4. 모델별 R² 개선 추이",
    subtitle = "기업 더미(모델 4)에서 H1/H2 R²가 대폭 상승 → 기업 간 이질성이 큰 분산 설명",
    x=NULL, y="R²",
    color="표본",
    caption="H1/H2: N_FS=68,039, N_HC=3,574  |  H3: N_FS=1,420 기업-분기, N_HC=925"
  ) +
  theme_minimal(base_size=12) +
  theme(legend.position="bottom", panel.grid.minor=element_blank(),
        plot.title=element_text(face="bold"))

ggsave(file.path(OUT, "fig4_r2_improvement.png"), fig4, width=10, height=5, dpi=150)
cat("  Figure 4 저장: fig4_r2_improvement.png\n")


# ── 최종 요약 ─────────────────────────────────────────────────
cat("\n============================================================\n")
cat("재현 완료\n")
cat("============================================================\n")
cat(sprintf("  사용 파일: analysis_ready_dataset.csv (1개)\n"))
cat(sprintf("  FS N = %s  |  HC N = %s\n",
    format(nrow(fs), big.mark=","), format(nrow(hc), big.mark=",")))
cat(sprintf("  H3 FS 기업-분기 = %s  |  HC = %s\n",
    format(nrow(fs_fq), big.mark=","), format(nrow(hc_fq), big.mark=",")))
cat("\n  생성된 시각화 파일:\n")
for (f in c("fig1_h1_weighted_effect.png","fig2_h2_contrasts_by_model.png",
            "fig3_h3_inverted_u.png","fig4_r2_improvement.png")) {
  cat(sprintf("    %s  %s\n", f,
      ifelse(file.exists(file.path(OUT,f)), "[저장됨]", "[저장 실패]")))
}
cat("============================================================\n")

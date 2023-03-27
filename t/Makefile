T = $(wildcard *.t)

test: $(T)
	@$(MAKE) --silent clean

$(T): clean
	./$@ $(TEST_OPTS)

clean:
	@rm -fr test-results

.PHONY: test $(T) clean
